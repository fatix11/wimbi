"""
CSV/XLSX parsing for uploads. Python's built-in `csv` plus `openpyxl` —
deliberately not pandas, which would be a far heavier dependency than
reading a header row and some values actually needs.
"""

import csv
import io

import openpyxl

MAX_PREVIEW_ROWS = 20


class ParseError(Exception):
    pass


def parse_upload(uploaded_file) -> tuple[list[str], list[dict]]:
    """Returns (column names, rows as dicts keyed by column name)."""
    name = (uploaded_file.name or "").lower()
    if name.endswith(".csv"):
        return _parse_csv(uploaded_file)
    if name.endswith((".xlsx", ".xlsm")):
        return _parse_xlsx(uploaded_file)
    raise ParseError("Unsupported file type — upload a .csv or .xlsx file.")


def _parse_csv(uploaded_file) -> tuple[list[str], list[dict]]:
    raw = uploaded_file.read()
    # Real exports arrive from Excel, Google Sheets and Kobo alike — a BOM
    # from any of them would otherwise corrupt the first column's name.
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ParseError("That file has no header row.")
    columns = [c.strip() for c in reader.fieldnames if c and c.strip()]
    rows = [{c: (row.get(c) or "").strip() for c in columns} for row in reader]
    return columns, rows


def _parse_xlsx(uploaded_file) -> tuple[list[str], list[dict]]:
    workbook = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
    sheet = workbook.active
    row_iter = sheet.iter_rows(values_only=True)
    try:
        header = next(row_iter)
    except StopIteration:
        raise ParseError("That spreadsheet is empty.")

    columns = [str(c).strip() for c in header if c is not None and str(c).strip()]
    if not columns:
        raise ParseError("That spreadsheet has no header row.")

    rows = []
    for values in row_iter:
        if values is None or all(v is None for v in values):
            continue
        row = {}
        for index, column in enumerate(columns):
            value = values[index] if index < len(values) else None
            row[column] = "" if value is None else str(value).strip()
        rows.append(row)
    workbook.close()
    return columns, rows


# Variables where several source columns are expected to map to the same
# name at once — a wide/pivoted file (one column per product, e.g. a Kobo
# distribution sheet's A_LEBBECK_SEEDLINGS, F_ALBIDA_SEEDLINGS...) has no
# other way to preserve every column's value. A plain dict keyed by
# variable name can't hold more than one value per key, so these
# accumulate into a list of {column, value} instead of overwriting.
MULTI_VALUE_VARIABLES = {"pivoted_product"}


def apply_mapping(rows: list[dict], column_mapping: dict[str, str]) -> list[dict]:
    """Rewrite each row from source column names to glossary variable names.
    Unmapped columns are dropped — they're visible in the mapping step, so
    this isn't silent."""
    mapped_rows = []
    for row in rows:
        mapped: dict = {}
        for column, variable in column_mapping.items():
            value = row.get(column, "")
            if variable in MULTI_VALUE_VARIABLES:
                mapped.setdefault(variable, []).append({"column": column, "value": value})
            else:
                mapped[variable] = value
        mapped_rows.append(mapped)
    return mapped_rows


def validate_rows(mapped_rows: list[dict], required: list[str]) -> list[tuple[dict, list[str]]]:
    """The quality gate. Every row needs its entity's required identifiers
    populated — a source id per transaction, an identifier per farmer — so
    each row stays traceable to its origin.

    Returns (row, errors) pairs rather than filtering: invalid rows are
    shown and excluded visibly, never silently dropped, and a bad row never
    rejects the whole file.
    """
    results = []
    for row in mapped_rows:
        errors = [f"Missing {name}" for name in required if not str(row.get(name, "")).strip()]
        results.append((row, errors))
    return results

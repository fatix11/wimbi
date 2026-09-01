"""
Streaming CSV -> Postgres COPY loader. Chunks rows so memory use stays
bounded regardless of file size — the same posture ADR-003 already accepts
for the eventual real sync (whatever tool ends up doing it, "load it in one
cheap batch, not row-by-row" is the right shape either way).
"""

import csv
import io
from pathlib import Path
from typing import Callable, NamedTuple

from django.db import connection


class ColumnSpec(NamedTuple):
    csv_header: str
    db_column: str
    transform: Callable[[str], str] | None = None


def load_csv(
    csv_path: Path,
    table: str,
    columns: list[ColumnSpec],
    required: list[str] | None = None,
    chunk_size: int = 50_000,
    stdout=None,
) -> tuple[int, int]:
    """Returns (loaded_count, skipped_count). Rows missing a value in any
    `required` csv_header are skipped rather than failing the whole load —
    real source data isn't always complete (e.g. some SF records have no
    email on file, and email is our lookup key)."""
    db_columns = [c.db_column for c in columns]
    copy_sql = (
        f"COPY analytics_mirror.{table} ({', '.join(db_columns)}) "
        "FROM STDIN WITH (FORMAT csv)"
    )
    required = required or []

    def flush(buf: io.StringIO) -> None:
        # A fresh cursor per chunk, not one held open across the whole
        # file — reusing a single cursor across ~100 copy_expert calls on
        # a wide table (55 columns) was observed to grow this process's
        # memory until a MemoryError around row 950k on sales_line. Root
        # cause not fully pinned down (the source file itself is clean —
        # verified separately), but a cursor per chunk is cheap and made
        # the same load complete cleanly.
        buf.seek(0)
        with connection.cursor() as cursor:
            cursor.copy_expert(copy_sql, buf)

    total = 0
    skipped = 0
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        buf = io.StringIO()
        writer = csv.writer(buf)
        buffered = 0

        for row in reader:
            if any(not row.get(field) for field in required):
                skipped += 1
                continue

            out_row = []
            for spec in columns:
                value = row[spec.csv_header]
                if value and spec.transform:
                    value = spec.transform(value)
                out_row.append(value)
            writer.writerow(out_row)
            buffered += 1
            total += 1

            if buffered >= chunk_size:
                flush(buf)
                buf = io.StringIO()
                writer = csv.writer(buf)
                buffered = 0
                if stdout:
                    stdout.write(f"  ...{total:,} rows loaded into {table}")

        if buffered:
            flush(buf)

    return total, skipped

"""
The upload flow: funnel → file → map → preview → save.

Follows the same pattern as farmers/views.py and accounts/views.py exactly
(@login_required, get_session_user, server-rendered templates + HTMX) —
no new frontend architecture, per ADR-010.
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import ADMIN_GROUP_NAME
from accounts.session import get_session_user

from . import glossary
from .models import UploadedDataset, UploadedRow
from .parsers import MAX_PREVIEW_ROWS, ParseError, apply_mapping, parse_upload, validate_rows

DATA_TEAM_GROUP_NAME = "Data Team"


def _can_access(request, dataset: UploadedDataset) -> bool:
    """v1.1 access: the uploader, plus Admin/Data Team. No new RBAC
    dimension — with effectively one user, program-scoped visibility would
    be speculative design (see _docs/bulk-uploader.md)."""
    if dataset.uploaded_by_id == request.user.id:
        return True
    return request.user.groups.filter(name__in=[ADMIN_GROUP_NAME, DATA_TEAM_GROUP_NAME]).exists()


def _get_dataset_or_403(request, pk: int) -> UploadedDataset:
    dataset = get_object_or_404(UploadedDataset, pk=pk)
    if not _can_access(request, dataset):
        raise PermissionDenied
    return dataset


@login_required
def dataset_list(request):
    datasets = UploadedDataset.objects.filter(uploaded_by=request.user)
    if request.user.groups.filter(name__in=[ADMIN_GROUP_NAME, DATA_TEAM_GROUP_NAME]).exists():
        datasets = UploadedDataset.objects.all()
    return render(request, "bulk_uploader/dataset_list.html", {"datasets": datasets.select_related("uploaded_by")})


@login_required
def upload_new(request):
    """Step 1 — the funnel (Country → Program → Data Type, ported from
    OAF's live Google Form) plus the file itself, on one screen."""
    context = {
        "countries": glossary.COUNTRIES,
        "programs": glossary.PROGRAMS,
        "data_types": [(key, label) for key, label, _entity in glossary.DATA_TYPES],
        "location_types": glossary.LOCATION_TYPES,
    }

    if request.method != "POST":
        return render(request, "bulk_uploader/upload_new.html", context)

    uploaded_file = request.FILES.get("file")
    country_code = request.POST.get("country_code", "").strip()
    program = request.POST.get("program", "").strip()
    # Data Type and Location type are both deliberately optional — see
    # glossary.entity_for_data_type.
    data_type = request.POST.get("data_type", "").strip()
    location_type = request.POST.get("location_type", "").strip()

    if not (uploaded_file and country_code and program):
        context["error"] = "Country, program, and a file are all required."
        return render(request, "bulk_uploader/upload_new.html", context, status=400)

    try:
        columns, rows = parse_upload(uploaded_file)
    except ParseError as exc:
        context["error"] = str(exc)
        return render(request, "bulk_uploader/upload_new.html", context, status=400)

    if not rows:
        context["error"] = "That file has a header but no data rows."
        return render(request, "bulk_uploader/upload_new.html", context, status=400)

    dataset = UploadedDataset.objects.create(
        country_code=country_code,
        program=program,
        data_type=data_type,
        entity=glossary.entity_for_data_type(data_type),
        location_type=location_type,
        operational_year=request.POST.get("operational_year", "").strip(),
        season=request.POST.get("season", "").strip(),
        notes=request.POST.get("notes", "").strip(),
        original_filename=uploaded_file.name,
        source_columns=columns,
        uploaded_by=request.user,
    )
    # raw_data (keyed by source column) is permanent history — mapped_data
    # is a derived result, recomputed from raw_data every time mapping is
    # saved, never the other way around. Keeps the file out of the picture
    # entirely — no MEDIA storage to configure or clean up.
    UploadedRow.objects.bulk_create(
        [UploadedRow(dataset=dataset, row_number=index + 1, raw_data=row) for index, row in enumerate(rows)]
    )
    return redirect("dataset_map", pk=dataset.pk)


@login_required
def dataset_edit(request, pk: int):
    """Correct the funnel answers (country/program/data type/season/notes)
    without re-uploading the file — the file and any mapping already done
    stay untouched. Reachable from the mapping page: there was previously
    no way back to the funnel at all short of abandoning the draft and
    starting over."""
    dataset = _get_dataset_or_403(request, pk)
    context = {
        "dataset": dataset,
        "countries": glossary.COUNTRIES,
        "programs": glossary.PROGRAMS,
        "data_types": [(key, label) for key, label, _entity in glossary.DATA_TYPES],
        "location_types": glossary.LOCATION_TYPES,
    }

    if request.method != "POST":
        return render(request, "bulk_uploader/dataset_edit.html", context)

    country_code = request.POST.get("country_code", "").strip()
    program = request.POST.get("program", "").strip()
    data_type = request.POST.get("data_type", "").strip()
    if not (country_code and program):
        context["error"] = "Country and program are required."
        return render(request, "bulk_uploader/dataset_edit.html", context, status=400)

    dataset.country_code = country_code
    dataset.program = program
    dataset.data_type = data_type
    dataset.entity = glossary.entity_for_data_type(data_type)
    dataset.location_type = request.POST.get("location_type", "").strip()
    dataset.operational_year = request.POST.get("operational_year", "").strip()
    dataset.season = request.POST.get("season", "").strip()
    dataset.notes = request.POST.get("notes", "").strip()
    # A changed entity changes what's required — any prior mapping/preview
    # is stale until re-validated, so send them through the map step again
    # rather than leaving a "saved" dataset silently validated against the
    # wrong entity's requirements.
    dataset.status = UploadedDataset.STATUS_DRAFT
    dataset.save(update_fields=[
        "country_code", "program", "data_type", "entity", "location_type",
        "operational_year", "season", "notes", "status",
    ])
    return redirect("dataset_map", pk=dataset.pk)


@login_required
def dataset_map(request, pk: int):
    """Step 2 — map source columns against the full glossary, grouped by
    entity. Not scoped to the funnel's chosen entity: real uploads are
    routinely multi-entity (see glossary.all_variables_grouped)."""
    dataset = _get_dataset_or_403(request, pk)
    groups = glossary.all_variables_grouped()
    all_variables = [variable for _group_name, variables in groups for variable in variables]

    if request.method == "POST":
        ignored = [c for c in dataset.source_columns if request.POST.get(f"ignore__{c}") == "1"]
        mapping = {}
        for column in dataset.source_columns:
            if column in ignored:
                continue  # ignore always wins over a stray leftover selection
            selected = request.POST.get(f"map__{column}", "").strip()
            if selected:
                mapping[column] = selected

        dataset.column_mapping = mapping
        dataset.ignored_columns = ignored
        dataset.status = UploadedDataset.STATUS_MAPPED
        dataset.save(update_fields=["column_mapping", "ignored_columns", "status"])

        required = glossary.required_variables(dataset.entity)
        rows = list(dataset.rows.all())
        # Always recompute from raw_data — never from the previous
        # mapped_data, which would compound each re-mapping pass on top of
        # the last instead of starting fresh from what was actually uploaded.
        raw_rows = [row.raw_data for row in rows]
        for row, (mapped, errors) in zip(rows, validate_rows(apply_mapping(raw_rows, mapping), required)):
            row.mapped_data = mapped
            row.is_valid = not errors
            row.validation_errors = errors
        UploadedRow.objects.bulk_update(rows, ["mapped_data", "is_valid", "validation_errors"])
        return redirect("dataset_preview", pk=dataset.pk)

    existing = dataset.column_mapping or glossary.suggest_mapping(dataset.source_columns, all_variables)
    ignored_set = set(dataset.ignored_columns)
    sample_rows = list(dataset.rows.all()[:5])
    columns = [
        {
            "name": column,
            "suggested": "" if column in ignored_set else existing.get(column, ""),
            "ignored": column in ignored_set,
            "samples": [str(row.raw_data.get(column, ""))[:40] for row in sample_rows],
        }
        for column in dataset.source_columns
    ]
    required_names = set(glossary.required_variables(dataset.entity))
    required_fields = [
        {"name": v.name, "label": v.label}
        for v in glossary.variables_for(dataset.entity) if v.name in required_names
    ]
    # Flat, JS-consumable, DEDUPED option list for the searchable combobox.
    # Several names (source_client_id, currency_code, unit_price_lcy...)
    # exist on purpose across multiple entities with the same meaning —
    # listing each as a separate option showed the exact same "Client ID
    # (lineage)" label 5 times with a near-arbitrary single group tag
    # (whichever entity happened to be built last won the JS-side lookup),
    # which is exactly why it looked directionless. One entry per name now,
    # tagged with every entity it actually applies to.
    by_name: dict[str, dict] = {}
    for group_name, variables in groups:
        for v in variables:
            entry = by_name.setdefault(v.name, {"name": v.name, "label": v.label, "groups": [], "required": False})
            entry["groups"].append(group_name)
            entry["required"] = entry["required"] or v.required
    variable_options = [
        {"name": e["name"], "label": e["label"], "group": " / ".join(e["groups"]), "required": e["required"]}
        for e in by_name.values()
    ]
    # The full-glossary progress scorecard — every variable across all 8
    # entities (deduped), tagged with its business-completeness tier. Only
    # required/nice_to_have surface in the tracker by request — "optional"
    # is real signal noise for a progress view (~30 of the ~50 variables),
    # even though the data stays in the glossary for mapping either way.
    tier_fields = [
        {"name": v.name, "label": v.label, "tier": v.tier}
        for v in glossary.all_variables_deduped()
        if v.tier in (glossary.TIER_REQUIRED, glossary.TIER_NICE_TO_HAVE)
    ]
    return render(
        request,
        "bulk_uploader/dataset_map.html",
        {
            "dataset": dataset,
            "columns": columns,
            "required_fields": required_fields,
            "variable_options": variable_options,
            "tier_fields": tier_fields,
        },
    )


@login_required
def dataset_preview(request, pk: int):
    """Step 3 — the quality gate, shown rather than enforced silently.
    Invalid rows are visible and excluded; they never reject the whole file."""
    dataset = _get_dataset_or_403(request, pk)

    if request.method == "POST":
        dataset.status = UploadedDataset.STATUS_SAVED
        dataset.save(update_fields=["status"])
        return redirect("dataset_list")

    mapped_variables = sorted(set(dataset.column_mapping.values()))

    def render_cell(value) -> str:
        # A multi-value variable (pivoted_product) stores a list of
        # {column, value} rather than a scalar — see parsers.MULTI_VALUE_VARIABLES.
        if isinstance(value, list):
            return ", ".join(f"{entry['column']}={entry['value']}" for entry in value if entry.get("value"))
        return str(value)

    # Cells are built here rather than in the template — Django templates
    # can't look a dict up by a loop variable's value.
    rows = [
        {
            "row_number": row.row_number,
            "cells": [render_cell(row.mapped_data.get(variable, "")) for variable in mapped_variables],
            "is_valid": row.is_valid,
            "validation_errors": row.validation_errors,
        }
        for row in dataset.rows.all()[:MAX_PREVIEW_ROWS]
    ]
    return render(
        request,
        "bulk_uploader/dataset_preview.html",
        {
            "dataset": dataset,
            "rows": rows,
            "mapped_variables": mapped_variables,
            "required": glossary.required_variables(dataset.entity),
            "valid_count": dataset.valid_row_count,
            "invalid_count": dataset.invalid_row_count,
            "total_count": dataset.rows.count(),
            "preview_limit": MAX_PREVIEW_ROWS,
        },
    )

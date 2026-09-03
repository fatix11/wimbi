"""
The upload flow: funnel → file → map → preview → save.

Follows the same pattern as farmers/views.py and accounts/views.py exactly
(@login_required, get_session_user, server-rendered templates + HTMX) —
no new frontend architecture, per ADR-010.
"""

import calendar
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import ADMIN_GROUP_NAME
from accounts.session import get_session_user
from analytics_mirror.models import DimCountry, DimProgram, DimSeason, DimSystem

from . import glossary
from .models import UploadedDataset, UploadedRow
from .parsers import (
    MAX_PREVIEW_ROWS,
    MULTI_VALUE_VARIABLES,
    ParseError,
    apply_mapping,
    build_synthetic_key,
    parse_upload,
    validate_rows,
)

DATA_TEAM_GROUP_NAME = "Data Team"
OTHER = "__other__"  # sentinel for a typed-in Program/Source system not in the real dims yet
EARLIEST_OPERATIONAL_YEAR = 2015


def _season_bounds(season: DimSeason) -> tuple[date, date] | None:
    if not (season.season_year and season.start_month and season.end_month):
        return None
    start = date(season.season_year, season.start_month, 1)
    end_year = season.season_year + 1 if season.crosses_year else season.season_year
    end = date(end_year, season.end_month, calendar.monthrange(end_year, season.end_month)[1])
    return start, end


def _closest_seasons(seasons: list[DimSeason], today: date, limit: int = 3) -> list[DimSeason]:
    """The 3 seasons (for one country) closest to today — 0 distance for a
    season today falls inside (the current one), otherwise the gap to
    whichever edge is nearer. In practice this surfaces the current season
    plus its immediate neighbors (the one just ended, the one coming up)
    rather than an arbitrary recency cutoff."""
    scored = []
    for season in seasons:
        bounds = _season_bounds(season)
        if not bounds:
            continue
        start, end = bounds
        gap = max((start - today).days, (today - end).days, 0)
        scored.append((gap, start, season))
    scored.sort(key=lambda t: (t[0], t[1]))
    closest = scored[:limit]
    closest.sort(key=lambda t: t[1])  # chronological for display, not by distance
    return [season for _gap, _start, season in closest]


def _funnel_dims() -> dict:
    """Country → Program → Source system (→ Season), sourced live from the
    real mirrored dims (DimCountry/DimProgram/DimSystem/DimSeason) rather
    than a second, driftable hardcoded copy (see glossary.py's note on
    this). Cascading is done client-side off one JSON payload, matching
    the existing searchable-combobox pattern on the mapping page, rather
    than an HTMX round-trip per keystroke.

    program_local_name (not program_oaf_eq) is the Program->Source-system
    cascade key: real data shows program_oaf_eq alone can collapse
    genuinely distinct programs within one country (Kenya has two separate
    "Retail" rows — "Asili - Cash (Walk-in)" and "(App)" — sharing one
    oaf_eq code), while program_local_name matches exactly what DimSystem's
    own rows use too.
    """
    countries = list(DimCountry.objects.exclude(country_code="").order_by("country_name").values_list("country_code", "country_name"))

    programs_by_country: dict[str, list[str]] = {}
    for country_code, local_name in DimProgram.objects.exclude(program_local_name="").order_by("country_code", "program_local_name").values_list("country_code", "program_local_name"):
        names = programs_by_country.setdefault(country_code, [])
        if local_name not in names:
            names.append(local_name)

    systems_by_key: dict[str, list[str]] = {}
    for country_code, local_name, system_name in DimSystem.objects.exclude(system_name="").order_by("country_code", "program_local_name", "system_name").values_list("country_code", "program_local_name", "system_name"):
        key = f"{country_code}||{local_name}"
        names = systems_by_key.setdefault(key, [])
        if system_name not in names:
            names.append(system_name)

    today = timezone.localdate()
    seasons_by_country_raw: dict[str, list[DimSeason]] = {}
    for season in DimSeason.objects.all():
        seasons_by_country_raw.setdefault(season.country_code, []).append(season)
    seasons_by_country: dict[str, list[dict]] = {}
    for country_code, seasons in seasons_by_country_raw.items():
        options = []
        for season in _closest_seasons(seasons, today):
            value = season.season_label or season.season_name
            if not value:
                continue
            text = value
            if season.season_name:
                text = f"{value} — {season.season_name}"
            if season.season_year_label:
                text += f" {season.season_year_label}"
            options.append({"value": value, "text": text})
        if options:
            seasons_by_country[country_code] = options

    current_year = timezone.localdate().year
    years = list(range(current_year, EARLIEST_OPERATIONAL_YEAR - 1, -1))  # most recent first

    return {
        "countries": countries,
        "programs_by_country": programs_by_country,
        "systems_by_key": systems_by_key,
        "seasons_by_country": seasons_by_country,
        "years": years,
    }


def _resolve_other(value: str, other_value: str) -> str:
    """The funnel's "Other…" option: the dropdown's own sentinel value
    never gets stored — whatever the uploader typed into the paired
    free-text field becomes the real, stored value instead."""
    return other_value.strip() if value == OTHER else value


def _column_stats(raw_rows: list[dict], column: str, total_rows: int) -> dict:
    """% unique and % blank for a source column, over every row (not just
    the 5-row sample) — a preliminary quality signal to help decide
    candidate keys before committing to a mapping or a synthetic
    combination. Blank counts as a real value for uniqueness purposes
    (matching how the save gate itself treats blank/whitespace-only as
    missing), so an all-blank column correctly shows near-zero uniqueness
    rather than a misleadingly high one."""
    if not total_rows:
        return {"unique_pct": 0, "blank_pct": 0}
    values = [str(row.get(column, "")).strip() for row in raw_rows]
    blank = sum(1 for v in values if v == "")
    distinct = len(set(values))
    return {
        "unique_pct": round(distinct / total_rows * 100),
        "blank_pct": round(blank / total_rows * 100),
    }


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
def glossary_page(request):
    """Every canonical variable the bulk uploader maps columns to, across
    all 8 entities — a general reference for what Wimbi's data model
    covers, not gated behind the uploader/Data Team access the dataset
    pages need, since it's schema/definition reference, not farmer data.
    Open to any logged-in user, same as Dashboard/Search."""
    name_entities: dict[str, list[str]] = {}
    for entity in glossary.ENTITIES.values():
        for v in entity.variables:
            name_entities.setdefault(v.name, []).append(entity.name)

    entities = []
    for entity in glossary.ENTITIES.values():
        variables = [
            {
                "name": v.name,
                "label": v.label,
                "description": v.description,
                "tier": v.tier,
                "required": v.required,
                "shared_with": [e for e in name_entities[v.name] if e != entity.name],
            }
            for v in entity.variables
        ]
        entities.append({"key": entity.key, "name": entity.name, "feeds": entity.feeds, "variables": variables})

    return render(
        request,
        "bulk_uploader/glossary_page.html",
        {
            "entities": entities,
            "total_raw": sum(len(e["variables"]) for e in entities),
            "total_deduped": len(name_entities),
            "shared_count": sum(1 for names in name_entities.values() if len(names) > 1),
        },
    )


@login_required
def upload_new(request):
    """Step 1 — the funnel (Country → Program → Source system → which
    entities this file involves) plus the file itself, on one screen."""
    context = {
        "funnel_dims": _funnel_dims(),
        "entity_choices": glossary.ENTITY_CHOICES,
        "location_types": glossary.LOCATION_TYPES,
    }

    if request.method != "POST":
        return render(request, "bulk_uploader/upload_new.html", context)

    uploaded_file = request.FILES.get("file")
    country_code = request.POST.get("country_code", "").strip()
    program = _resolve_other(request.POST.get("program", "").strip(), request.POST.get("program_other", ""))
    source_system = _resolve_other(request.POST.get("source_system", "").strip(), request.POST.get("source_system_other", ""))
    location_type = _resolve_other(request.POST.get("location_type", "").strip(), request.POST.get("location_type_other", ""))
    entities = [key for key in request.POST.getlist("entities") if key in glossary.ENTITIES]
    operational_year = request.POST.get("operational_year", "").strip()
    season = request.POST.get("season", "").strip()
    context.update({
        "selected_entities": entities,
        "selected_country": country_code,
        "selected_program": program,
        "selected_source_system": source_system,
        "selected_location_type": location_type,
        "selected_operational_year": operational_year,
        "selected_season": season,
    })

    if not (uploaded_file and country_code and program and entities):
        context["error"] = "Country, program, at least one entity, and a file are all required."
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
        source_system=source_system,
        entities=entities,
        location_type=location_type,
        operational_year=operational_year,
        season=season,
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
    """Correct the funnel answers (country/program/entities/season/notes)
    without re-uploading the file — the file and any mapping already done
    stay untouched. Reachable from the mapping page: there was previously
    no way back to the funnel at all short of abandoning the draft and
    starting over."""
    dataset = _get_dataset_or_403(request, pk)
    context = {
        "dataset": dataset,
        "funnel_dims": _funnel_dims(),
        "entity_choices": glossary.ENTITY_CHOICES,
        "location_types": glossary.LOCATION_TYPES,
    }

    if request.method != "POST":
        return render(request, "bulk_uploader/dataset_edit.html", context)

    country_code = request.POST.get("country_code", "").strip()
    program = _resolve_other(request.POST.get("program", "").strip(), request.POST.get("program_other", ""))
    source_system = _resolve_other(request.POST.get("source_system", "").strip(), request.POST.get("source_system_other", ""))
    location_type = _resolve_other(request.POST.get("location_type", "").strip(), request.POST.get("location_type_other", ""))
    entities = [key for key in request.POST.getlist("entities") if key in glossary.ENTITIES]
    if not (country_code and program and entities):
        context["error"] = "Country, program, and at least one entity are required."
        return render(request, "bulk_uploader/dataset_edit.html", context, status=400)

    dataset.country_code = country_code
    dataset.program = program
    dataset.source_system = source_system
    dataset.entities = entities
    dataset.location_type = location_type
    dataset.operational_year = request.POST.get("operational_year", "").strip()
    dataset.season = request.POST.get("season", "").strip()
    dataset.notes = request.POST.get("notes", "").strip()
    # Changed entities change what's required — any prior mapping/preview
    # is stale until re-validated, so send them through the map step again
    # rather than leaving a "saved" dataset silently validated against the
    # wrong requirements.
    dataset.status = UploadedDataset.STATUS_DRAFT
    dataset.save(update_fields=[
        "country_code", "program", "source_system", "entities", "location_type",
        "operational_year", "season", "notes", "status",
    ])
    return redirect("dataset_map", pk=dataset.pk)


@login_required
def dataset_map(request, pk: int):
    """Step 2 — map source columns against the variables of just the
    entities checked on the funnel (see glossary.entities_grouped) — a
    real upload is routinely multi-entity, but no longer unrestricted
    across all 8: the entities checklist now says exactly which apply."""
    dataset = _get_dataset_or_403(request, pk)
    grouped = glossary.entities_grouped(dataset.entities)
    all_variables = [variable for _key, _group_name, variables in grouped for variable in variables]
    required = glossary.required_variables_for_entities(dataset.entities)
    required_names = set(required)

    if request.method == "POST":
        ignored = [c for c in dataset.source_columns if request.POST.get(f"ignore__{c}") == "1"]
        mapping = {}
        for column in dataset.source_columns:
            if column in ignored:
                continue  # ignore always wins over a stray leftover selection
            selected = request.POST.get(f"map__{column}", "").strip()
            if selected:
                mapping[column] = selected

        # Synthetic composite keys — only for the entities' actual required
        # lineage fields (the concrete "no clean source id" problem), and
        # only kept if 2+ columns are actually chosen (a single column is
        # just a normal mapping, not a combination).
        synthetic_keys = {}
        for variable_name in required_names:
            chosen = [c for c in request.POST.getlist(f"synth__{variable_name}") if c in dataset.source_columns]
            if len(chosen) >= 2:
                synthetic_keys[variable_name] = chosen

        dataset.column_mapping = mapping
        dataset.ignored_columns = ignored
        dataset.synthetic_keys = synthetic_keys
        dataset.status = UploadedDataset.STATUS_MAPPED
        dataset.save(update_fields=["column_mapping", "ignored_columns", "synthetic_keys", "status"])

        rows = list(dataset.rows.all())
        # Always recompute from raw_data — never from the previous
        # mapped_data, which would compound each re-mapping pass on top of
        # the last instead of starting fresh from what was actually uploaded.
        raw_rows = [row.raw_data for row in rows]
        mapped_rows = apply_mapping(raw_rows, mapping)
        for mapped_row, raw_row in zip(mapped_rows, raw_rows):
            if dataset.source_system:
                # Broadcast the funnel's resolved source_system onto every
                # row, like "SELECT 'KOBO' AS source_system" applied to the
                # whole file — a real upload almost never carries its own
                # per-row source_system column. An explicit per-row mapped
                # value (the rare genuinely mixed-system file) still wins.
                if not mapped_row.get("source_system"):
                    mapped_row["source_system"] = dataset.source_system
            for variable_name, columns in synthetic_keys.items():
                if not mapped_row.get(variable_name):
                    synthetic_value = build_synthetic_key(raw_row, columns)
                    if synthetic_value:
                        mapped_row[variable_name] = synthetic_value
        for row, (mapped, errors) in zip(rows, validate_rows(mapped_rows, required)):
            row.mapped_data = mapped
            row.is_valid = not errors
            row.validation_errors = errors
        UploadedRow.objects.bulk_update(rows, ["mapped_data", "is_valid", "validation_errors"])
        return redirect("dataset_preview", pk=dataset.pk)

    existing = dataset.column_mapping or glossary.suggest_mapping(dataset.source_columns, all_variables)
    ignored_set = set(dataset.ignored_columns)
    sample_rows = list(dataset.rows.all()[:5])
    all_raw_rows = list(dataset.rows.values_list("raw_data", flat=True))
    total_rows = len(all_raw_rows)
    columns = [
        {
            "name": column,
            "suggested": "" if column in ignored_set else existing.get(column, ""),
            "ignored": column in ignored_set,
            "samples": [str(row.raw_data.get(column, ""))[:40] for row in sample_rows],
            "stats": _column_stats(all_raw_rows, column, total_rows),
        }
        for column in dataset.source_columns
    ]
    required_fields = [
        {"name": v.name, "label": v.label, "synthetic_columns": dataset.synthetic_keys.get(v.name, [])}
        for v in glossary.variables_deduped_for(dataset.entities) if v.name in required_names
    ]
    # Flat, JS-consumable, DEDUPED option list for the searchable combobox.
    # Several names (source_client_id, currency_code, unit_price_lcy...)
    # exist on purpose across multiple entities with the same meaning —
    # listing each as a separate option showed the exact same "Client ID
    # (lineage)" label 5 times with a near-arbitrary single group tag
    # (whichever entity happened to be built last won the JS-side lookup),
    # which is exactly why it looked directionless. One entry per name now,
    # tagged with every checked entity it actually applies to.
    by_name: dict[str, dict] = {}
    for _key, group_name, variables in grouped:
        for v in variables:
            if v.name == "source_system" and dataset.source_system:
                continue  # locked by the funnel — see the banner instead, not choosable per-column
            entry = by_name.setdefault(v.name, {"name": v.name, "label": v.label, "groups": [], "required": False})
            entry["groups"].append(group_name)
            entry["required"] = entry["required"] or v.required
    variable_options = [
        {"name": e["name"], "label": e["label"], "group": " / ".join(e["groups"]), "required": e["required"]}
        for e in by_name.values()
    ]
    # The progress scorecard — every variable across just the checked
    # entities (deduped), tagged with its business-completeness tier. Only
    # required/nice_to_have surface in the tracker by request — "optional"
    # is real signal noise for a progress view, even though the data stays
    # in the glossary for mapping either way.
    tier_fields = [
        {"name": v.name, "label": v.label, "tier": v.tier}
        for v in glossary.variables_deduped_for(dataset.entities)
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
            "locked_source_system": bool(dataset.source_system),
            "multi_value_variables": list(MULTI_VALUE_VARIABLES),
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

    mapped_variables = set(dataset.column_mapping.values())
    if dataset.source_system:
        mapped_variables.add("source_system")  # broadcast, not a real column mapping — see dataset_map
    mapped_variables.update(dataset.synthetic_keys.keys())  # composite-key-derived, not a real column mapping either
    mapped_variables = sorted(mapped_variables)

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
            "synthetic_variable_names": set(dataset.synthetic_keys.keys()),
            "valid_count": dataset.valid_row_count,
            "invalid_count": dataset.invalid_row_count,
            "total_count": dataset.rows.count(),
            "preview_limit": MAX_PREVIEW_ROWS,
        },
    )

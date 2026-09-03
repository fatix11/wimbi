"""Bulk Data Mapper/Uploader v1.1 — see _docs/bulk-uploader.md."""

import io

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.provisioning import get_or_provision_user
from bulk_uploader import glossary
from bulk_uploader.models import UploadedDataset
from bulk_uploader.parsers import ParseError, apply_mapping, parse_upload, validate_rows
from bulk_uploader.glossary import ENTITIES


def login_as(client, email):
    user = get_or_provision_user(email)
    client.force_login(user)
    return user


def sales_csv(rows=None):
    rows = rows or [
        "TXN-1,ORD-1,MW-001,Hybrid Maize Seed,10,1200",
        "TXN-2,ORD-2,MW-002,Albizia Lebbeck,50,370",
    ]
    body = "transaction_id,order_id,client_id,product,quantity,unit_price\n" + "\n".join(rows)
    return SimpleUploadedFile("sales.csv", body.encode("utf-8"), content_type="text/csv")


# --- glossary ---------------------------------------------------------

def test_funnel_data_type_picks_the_entity():
    assert glossary.DATA_TYPE_ENTITY["distributions"] == "sale"
    assert glossary.DATA_TYPE_ENTITY["registration"] == "client"
    assert glossary.DATA_TYPE_ENTITY["payments"] == "payment"


def test_client_identity_columns_are_not_required():
    """DIM_CLIENT has three real, separate identity columns (national_id,
    account_number, fineract_id) — none required, since dims/Programs.csv
    shows the identifier scheme genuinely varies by country (NID/
    APPSHEET_ID/ACCOUNTNUMBER/none). Requiring one specific column would
    reject most of Malawi outright."""
    required = glossary.required_variables("client")
    assert "national_id" not in required
    assert "account_number" not in required
    assert "fineract_id" not in required
    # What IS required: a name, and lineage back to the source record.
    assert set(required) == {"full_name", "source_system", "source_client_id"}


def test_entities_require_their_real_lineage_id():
    """Each entity's required field is its actual warehouse lineage column,
    not a generic invented one — confirmed against facts.sql."""
    assert glossary.required_variables("sale") == ["source_transaction_id"]
    assert glossary.required_variables("purchase") == ["source_purchase_id"]
    assert glossary.required_variables("payment") == ["source_transaction_id"]
    assert glossary.required_variables("loan") == ["source_loan_id"]


def test_suggest_mapping_matches_on_name_case_and_separator_insensitively():
    variables = glossary.variables_for("sale")
    suggested = glossary.suggest_mapping(["Source Transaction ID", "UNIT_PRICE_LCY", "nonsense"], variables)
    assert suggested["Source Transaction ID"] == "source_transaction_id"
    assert suggested["UNIT_PRICE_LCY"] == "unit_price_lcy"
    assert "nonsense" not in suggested


def test_naive_matching_misses_labels_not_matching_name_or_label():
    """suggest_mapping matches on the variable's name OR its label ("Transaction
    ID" catches source_transaction_id that way) — but a column named
    something else reasonable, like the real Malawi file's "UNIQUE_FARMERID"
    (→ source_client_id conceptually), matches neither and needs a human or
    real AI-assisted suggestion (v1.2+) to close the gap."""
    variables = glossary.variables_for("client")
    suggested = glossary.suggest_mapping(["UNIQUE_FARMERID"], variables)
    assert "UNIQUE_FARMERID" not in suggested


# --- glossary restructuring (2026-09-03) -------------------------------

def test_service_roles_live_under_people_not_sale():
    """DIM_PEOPLE's own real sourcing unions field_officer/shopkeeper/
    nursery_manager as staff roles — they're not sale attributes."""
    sale_names = {v.name for v in ENTITIES["sale"].variables}
    people_names = {v.name for v in ENTITIES["people"].variables}
    for role in ("field_officer", "shopkeeper", "nursery_manager"):
        assert role not in sale_names
        assert role in people_names


def test_people_has_no_generic_full_name():
    """Once the three specific roles exist, a generic "Full name" would be
    ambiguous — which one should a mapper pick for a staff column?"""
    people_names = {v.name for v in ENTITIES["people"].variables}
    assert "full_name" not in people_names


def test_tier_is_independent_of_the_strict_required_gate():
    """Sale's product_name/quantity/unit_price_lcy are tier="required" (the
    business-completeness scorecard, restoring the Data Collection
    Template's original bar) but required=False (the strict save gate) —
    broadening the gate would reject every real Kobo Trees sale outright,
    since that data genuinely has no pricing (GAP-001)."""
    from bulk_uploader import glossary

    sale_by_name = {v.name: v for v in ENTITIES["sale"].variables}
    assert sale_by_name["product_name"].tier == glossary.TIER_REQUIRED
    assert sale_by_name["product_name"].required is False
    assert sale_by_name["source_transaction_id"].tier == glossary.TIER_REQUIRED
    assert sale_by_name["source_transaction_id"].required is True  # this one IS gated


def test_new_location_fields_added_ahead_of_the_real_dwh():
    """village/cell/source_location_id were added on request even though
    the real DIM_LOCATION (confirmed via direct DDL read) has none of
    them — tracked in upstream-gaps.md GAP-004 for the user to add for
    real later."""
    location_names = {v.name for v in ENTITIES["location"].variables}
    assert {"village", "cell", "source_location_id"} <= location_names
    assert "loc_type" not in location_names  # moved to the funnel instead


def test_all_variables_deduped_has_one_entry_per_name():
    from bulk_uploader import glossary

    deduped = glossary.all_variables_deduped()
    names = [v.name for v in deduped]
    assert len(names) == len(set(names))
    assert "source_client_id" in names  # present once, not five times


def test_client_still_has_its_own_full_name():
    client_names = {v.name for v in ENTITIES["client"].variables}
    assert "full_name" in client_names


# --- parsing / validation ---------------------------------------------

def test_parse_csv_reads_headers_and_rows():
    columns, rows = parse_upload(sales_csv())
    assert columns[0] == "transaction_id"
    assert len(rows) == 2
    assert rows[0]["product"] == "Hybrid Maize Seed"


def test_parse_csv_strips_a_bom():
    """Exports from Excel/Sheets/Kobo routinely carry a BOM — left alone it
    corrupts the first column's name and breaks its mapping."""
    body = "﻿transaction_id,quantity\nTXN-1,10"
    columns, _rows = parse_upload(SimpleUploadedFile("x.csv", body.encode("utf-8"), content_type="text/csv"))
    assert columns[0] == "transaction_id"


def test_parse_rejects_unsupported_file_types():
    with pytest.raises(ParseError):
        parse_upload(SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain"))


def test_pivoted_product_columns_are_preserved_not_overwritten():
    """A wide/pivoted file (one column per product, e.g. the real
    mw_seedlings_distribution_data.csv's A_LEBBECK_SEEDLINGS,
    F_ALBIDA_SEEDLINGS...) maps several source columns to the same
    "pivoted_product" variable — a plain dict would have the last one
    silently overwrite the rest."""
    mapped = apply_mapping(
        [{"A_LEBBECK_SEEDLINGS": "9", "F_ALBIDA_SEEDLINGS": "2", "unrelated": "x"}],
        {"A_LEBBECK_SEEDLINGS": "pivoted_product", "F_ALBIDA_SEEDLINGS": "pivoted_product", "unrelated": "quantity"},
    )
    entries = mapped[0]["pivoted_product"]
    assert len(entries) == 2
    assert {"column": "A_LEBBECK_SEEDLINGS", "value": "9"} in entries
    assert {"column": "F_ALBIDA_SEEDLINGS", "value": "2"} in entries
    assert mapped[0]["quantity"] == "x"


def test_validation_flags_rows_missing_a_required_id():
    mapped = apply_mapping(
        [{"txn": "TXN-1", "qty": "10"}, {"txn": "", "qty": "5"}],
        {"txn": "source_transaction_id", "qty": "quantity"},
    )
    results = validate_rows(mapped, glossary.required_variables("sale"))
    assert results[0][1] == []
    assert results[1][1] == ["Missing source_transaction_id"]


# --- flow -------------------------------------------------------------

@pytest.mark.django_db
def test_upload_requires_login(client):
    assert client.get("/uploads/").status_code == 302
    assert client.get("/uploads/new/").status_code == 302


@pytest.mark.django_db
def test_full_upload_map_validate_save_flow(client, mirror_data):
    login_as(client, "data.team@oneacrefund.org")

    response = client.post("/uploads/new/", {
        "country_code": "RW", "program": "Core", "data_type": "distributions",
        "operational_year": "2026", "season": "LR26", "file": sales_csv(),
    })
    assert response.status_code == 302
    dataset = UploadedDataset.objects.get()
    assert dataset.entity == "sale"  # funnel picked it
    assert dataset.rows.count() == 2

    # Mapping step pre-fills exact name-or-label matches — "transaction_id"
    # catches source_transaction_id via its "Transaction ID" label.
    response = client.get(f"/uploads/{dataset.pk}/map/")
    assert response.status_code == 200
    assert response.context["columns"][0]["suggested"] == "source_transaction_id"

    response = client.post(f"/uploads/{dataset.pk}/map/", {
        "map__transaction_id": "source_transaction_id",
        "map__client_id": "source_client_id",
        "map__quantity": "quantity",
    })
    assert response.status_code == 302
    dataset.refresh_from_db()
    assert dataset.status == UploadedDataset.STATUS_MAPPED
    assert dataset.valid_row_count == 2

    response = client.get(f"/uploads/{dataset.pk}/preview/")
    assert response.status_code == 200
    assert response.context["valid_count"] == 2

    response = client.post(f"/uploads/{dataset.pk}/preview/")
    assert response.status_code == 302
    dataset.refresh_from_db()
    assert dataset.status == UploadedDataset.STATUS_SAVED


@pytest.mark.django_db
def test_invalid_rows_are_flagged_not_dropped(client, mirror_data):
    """The quality gate is visible, not silently destructive — a bad row
    never rejects the whole file and never disappears."""
    login_as(client, "data.team@oneacrefund.org")
    client.post("/uploads/new/", {
        "country_code": "RW", "program": "Core", "data_type": "distributions",
        "file": sales_csv(rows=["TXN-1,ORD-1,MW-001,Seed,10,1200", ",ORD-2,MW-002,Tubes,50,370"]),
    })
    dataset = UploadedDataset.objects.get()
    client.post(f"/uploads/{dataset.pk}/map/", {"map__transaction_id": "source_transaction_id"})

    assert dataset.rows.count() == 2, "the invalid row must still exist"
    assert dataset.valid_row_count == 1
    assert dataset.invalid_row_count == 1
    assert dataset.rows.get(is_valid=False).validation_errors == ["Missing source_transaction_id"]


@pytest.mark.django_db
def test_upload_is_hidden_from_an_unrelated_user(client, mirror_data):
    owner = login_as(client, "data.team@oneacrefund.org")
    client.post("/uploads/new/", {
        "country_code": "RW", "program": "Core", "data_type": "distributions", "file": sales_csv(),
    })
    dataset = UploadedDataset.objects.get()
    assert dataset.uploaded_by == owner

    client.logout()
    other = get_or_provision_user("cc.malawi@oneacrefund.org")
    other.groups.remove(*other.groups.filter(name__in=["Admin", "Data Team"]))
    client.force_login(other)

    assert client.get(f"/uploads/{dataset.pk}/preview/").status_code == 403
    assert client.get("/uploads/").context["datasets"].count() == 0


@pytest.mark.django_db
def test_pivoted_product_survives_the_full_map_and_save_flow(client, mirror_data):
    login_as(client, "data.team@oneacrefund.org")
    body = "transaction_id,species_a,species_b\nTXN-1,9,2\nTXN-2,5,0\n"
    upload = SimpleUploadedFile("seedlings.csv", body.encode(), content_type="text/csv")
    client.post("/uploads/new/", {
        "country_code": "MW", "program": "Trees", "data_type": "distributions", "file": upload,
    })
    dataset = UploadedDataset.objects.get()

    client.post(f"/uploads/{dataset.pk}/map/", {
        "map__transaction_id": "source_transaction_id",
        "map__species_a": "pivoted_product",
        "map__species_b": "pivoted_product",
    })
    dataset.refresh_from_db()
    assert dataset.valid_row_count == 2

    row = dataset.rows.get(row_number=1)
    entries = row.mapped_data["pivoted_product"]
    assert {"column": "species_a", "value": "9"} in entries
    assert {"column": "species_b", "value": "2"} in entries

    # The preview page must render the list without crashing on a raw
    # Python repr.
    response = client.get(f"/uploads/{dataset.pk}/preview/")
    assert response.status_code == 200
    assert b"species_a=9" in response.content


@pytest.mark.django_db
def test_sample_values_survive_a_second_visit_to_the_mapping_page(client, mirror_data):
    """Real bug, found live: mapped_data used to be rewritten in place from
    source-column keys to variable-name keys on the first mapping save, so
    re-visiting the mapping page a second time showed blank samples (the
    lookup used the original source column name, which no longer existed
    as a key). raw_data is the fix — permanent, never overwritten."""
    login_as(client, "data.team@oneacrefund.org")
    client.post("/uploads/new/", {
        "country_code": "RW", "program": "Core", "data_type": "distributions", "file": sales_csv(),
    })
    dataset = UploadedDataset.objects.get()

    # First visit: samples present.
    first_visit = client.get(f"/uploads/{dataset.pk}/map/")
    assert first_visit.context["columns"][0]["samples"] == ["TXN-1", "TXN-2"]

    # Save a mapping — this used to be the moment mapped_data got
    # overwritten and samples broke on the next visit.
    client.post(f"/uploads/{dataset.pk}/map/", {"map__transaction_id": "source_transaction_id"})

    second_visit = client.get(f"/uploads/{dataset.pk}/map/")
    assert second_visit.context["columns"][0]["samples"] == ["TXN-1", "TXN-2"]


@pytest.mark.django_db
def test_remapping_recomputes_from_raw_data_not_the_prior_mapped_result(client, mirror_data):
    """A second mapping pass must start fresh from what was actually
    uploaded, not compound on top of whatever the previous pass produced."""
    login_as(client, "data.team@oneacrefund.org")
    client.post("/uploads/new/", {
        "country_code": "RW", "program": "Core", "data_type": "distributions", "file": sales_csv(),
    })
    dataset = UploadedDataset.objects.get()

    client.post(f"/uploads/{dataset.pk}/map/", {"map__transaction_id": "source_transaction_id"})
    client.post(f"/uploads/{dataset.pk}/map/", {"map__quantity": "quantity"})  # different mapping entirely

    dataset.refresh_from_db()
    row = dataset.rows.get(row_number=1)
    assert row.mapped_data == {"quantity": "10"}  # not source_transaction_id from the first pass


def test_variable_options_are_deduped_across_entities():
    """source_client_id (and similar lineage fields) intentionally exist on
    5 different entities with the same meaning — showing 5 separate
    identical-looking options, each tagged with an almost arbitrary single
    entity, was exactly why they looked directionless. One entry per name,
    tagged with every entity it applies to."""
    from bulk_uploader import glossary

    groups = glossary.all_variables_grouped()
    by_name: dict[str, dict] = {}
    for group_name, variables in groups:
        for v in variables:
            entry = by_name.setdefault(v.name, {"groups": []})
            entry["groups"].append(group_name)

    client_id_groups = by_name["source_client_id"]["groups"]
    assert len(client_id_groups) >= 4  # Client, Sale, Purchase, Loan, Payment
    assert len(set(client_id_groups)) == len(client_id_groups)  # no entity listed twice


@pytest.mark.django_db
def test_location_type_is_an_optional_funnel_field(client, mirror_data):
    """A single upload is virtually always one place-type throughout — this
    is funnel-level (like Country/Program), not a per-row mapped column,
    and it shouldn't block an upload if left unset."""
    login_as(client, "data.team@oneacrefund.org")
    response = client.post("/uploads/new/", {
        "country_code": "MW", "program": "Trees", "location_type": "Nursery", "file": sales_csv(),
    })
    assert response.status_code == 302
    dataset = UploadedDataset.objects.get()
    assert dataset.location_type == "Nursery"

    # Also editable afterward without re-uploading.
    client.post(f"/uploads/{dataset.pk}/edit/", {
        "country_code": "MW", "program": "Trees", "location_type": "Shop",
    })
    dataset.refresh_from_db()
    assert dataset.location_type == "Shop"


@pytest.mark.django_db
def test_ignored_column_is_excluded_even_if_it_also_has_a_stray_selection(client, mirror_data):
    """Ignore always wins over a leftover/stale mapping selection — found
    live-testing a real file where a checksum column (TOTAL_SEEDLINGS) had
    accidentally been left mapped to "Full name" from earlier testing."""
    login_as(client, "data.team@oneacrefund.org")
    client.post("/uploads/new/", {
        "country_code": "RW", "program": "Core", "data_type": "distributions", "file": sales_csv(),
    })
    dataset = UploadedDataset.objects.get()

    client.post(f"/uploads/{dataset.pk}/map/", {
        "map__transaction_id": "source_transaction_id",
        "map__product": "product_name",  # a stray selection on a column we'll also mark ignored
        "ignore__product": "1",
    })
    dataset.refresh_from_db()
    assert dataset.ignored_columns == ["product"]
    assert "product" not in dataset.column_mapping
    row = dataset.rows.get(row_number=1)
    assert "product_name" not in row.mapped_data


@pytest.mark.django_db
def test_ignored_state_persists_across_a_second_visit(client, mirror_data):
    login_as(client, "data.team@oneacrefund.org")
    client.post("/uploads/new/", {
        "country_code": "RW", "program": "Core", "data_type": "distributions", "file": sales_csv(),
    })
    dataset = UploadedDataset.objects.get()
    client.post(f"/uploads/{dataset.pk}/map/", {"ignore__product": "1"})

    response = client.get(f"/uploads/{dataset.pk}/map/")
    product_col = next(c for c in response.context["columns"] if c["name"] == "product")
    assert product_col["ignored"] is True
    assert product_col["suggested"] == ""


@pytest.mark.django_db
def test_data_type_is_optional_and_defaults_to_client_entity(client, mirror_data):
    """An uploader unsure what kind of data this is shouldn't be blocked
    from uploading — omitting data_type must still succeed."""
    login_as(client, "data.team@oneacrefund.org")
    response = client.post("/uploads/new/", {
        "country_code": "RW", "program": "Core", "file": sales_csv(),
    })
    assert response.status_code == 302
    dataset = UploadedDataset.objects.get()
    assert dataset.data_type == ""
    assert dataset.entity == "client"


@pytest.mark.django_db
def test_dataset_edit_updates_funnel_fields_without_touching_the_file(client, mirror_data):
    login_as(client, "data.team@oneacrefund.org")
    client.post("/uploads/new/", {
        "country_code": "RW", "program": "Core", "data_type": "distributions", "file": sales_csv(),
    })
    dataset = UploadedDataset.objects.get()
    original_row_count = dataset.rows.count()

    response = client.post(f"/uploads/{dataset.pk}/edit/", {
        "country_code": "KE", "program": "Retail", "data_type": "registration", "season": "LR26",
    })
    assert response.status_code == 302
    dataset.refresh_from_db()
    assert dataset.country_code == "KE"
    assert dataset.program == "Retail"
    assert dataset.entity == "client"  # re-derived from the new data_type
    assert dataset.season == "LR26"
    assert dataset.rows.count() == original_row_count  # file untouched


@pytest.mark.django_db
def test_dataset_edit_resets_status_since_required_fields_may_change(client, mirror_data):
    login_as(client, "data.team@oneacrefund.org")
    client.post("/uploads/new/", {
        "country_code": "RW", "program": "Core", "data_type": "distributions", "file": sales_csv(),
    })
    dataset = UploadedDataset.objects.get()
    client.post(f"/uploads/{dataset.pk}/map/", {"map__transaction_id": "source_transaction_id"})
    dataset.refresh_from_db()
    assert dataset.status == UploadedDataset.STATUS_MAPPED

    client.post(f"/uploads/{dataset.pk}/edit/", {
        "country_code": "RW", "program": "Core", "data_type": "registration",
    })
    dataset.refresh_from_db()
    assert dataset.status == UploadedDataset.STATUS_DRAFT


@pytest.mark.django_db
def test_data_team_can_see_other_peoples_uploads(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    client.post("/uploads/new/", {
        "country_code": "MW", "program": "Trees", "data_type": "distributions", "file": sales_csv(),
    })
    dataset = UploadedDataset.objects.get()

    client.logout()
    data_team = get_or_provision_user("data.team@oneacrefund.org")
    data_team.groups.add(Group.objects.get_or_create(name="Data Team")[0])
    client.force_login(data_team)

    assert client.get(f"/uploads/{dataset.pk}/preview/").status_code == 200
    assert client.get("/uploads/").context["datasets"].count() == 1

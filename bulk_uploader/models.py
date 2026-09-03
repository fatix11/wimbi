"""
Wimbi's own operational tables for uploaded program data (ADR-004) — these
are genuinely owned and written by the app, unlike analytics_mirror's
read-only, sync-owned mirror of ANALYTICS. Deliberately in the default
`public` schema, well away from analytics_mirror (see ADR-006's schema
isolation lesson).

Requirements and phasing: _docs/bulk-uploader.md
"""

from django.contrib.auth.models import User
from django.db import models

from .glossary import ENTITIES, LOCATION_TYPES


class UploadedDataset(models.Model):
    """One uploaded file, plus the funnel answers that scope it and the
    column mapping the uploader confirmed."""

    STATUS_DRAFT = "draft"
    STATUS_MAPPED = "mapped"
    STATUS_SAVED = "saved"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft — uploaded, not yet mapped"),
        (STATUS_MAPPED, "Mapped — columns mapped, not yet committed"),
        (STATUS_SAVED, "Saved — rows committed"),
    ]

    # The funnel (Country → Program → Entities). Beyond scoping the mapping
    # UI, these tag the upload for whichever promotion-to-SOURCES path it
    # eventually needs (v1.2+).
    country_code = models.CharField(max_length=8)
    program = models.CharField(max_length=64)
    # Which system this file's data came from (KOBO, ODOO, FINERACT...),
    # sourced from the real DimSystem cascade off country+program. Broadcast
    # into every row's mapped_data as a locked constant (see dataset_map) —
    # a real upload almost never carries its own per-row source_system
    # column, since the whole file already comes from one system by
    # definition. Left blank, source_system stays a normal mappable
    # variable for the rare file that genuinely does mix systems per row.
    source_system = models.CharField(max_length=64, blank=True)
    # Which of the 8 glossary entities this file involves — one or many
    # (a real Kobo distribution sheet routinely carries Client, Location,
    # People, AND Sale columns at once). Replaced the earlier single-guess
    # "Data Type" field (2026-09-03): Data Type only loosely implied one
    # entity and left real multi-entity files under-served. This list
    # directly decides the save gate (required_variables_for_entities) and
    # scopes which variables the mapping dropdown offers. Editable after
    # upload via dataset_edit, without re-uploading.
    entities = models.JSONField(default=list)
    # A single upload is virtually always one place-type throughout (all
    # nursery, all shop...) — funnel-level for the same reason Country and
    # Program already are, rather than a per-row mapped column.
    location_type = models.CharField(max_length=16, choices=[(t, t) for t in LOCATION_TYPES], blank=True)
    operational_year = models.CharField(max_length=16, blank=True)
    season = models.CharField(max_length=32, blank=True)
    notes = models.TextField(blank=True)

    original_filename = models.CharField(max_length=255)
    source_columns = models.JSONField(default=list)
    # {source column name: glossary variable name} — the mapping decision
    # itself is recorded, not just its result, so it stays auditable and
    # can seed a suggested mapping for the same dataset next season (v1.2+).
    column_mapping = models.JSONField(default=dict)
    # {glossary variable name: [source column names]} — for a required
    # lineage id with no single clean source column, a composite key built
    # by hashing 2+ chosen columns together (parsers.build_synthetic_key),
    # tagged as lower-confidence/"synthetic" the same way a funnel-broadcast
    # value (source_system) is: dataset-level, applied to every row, and
    # only used where no real per-row mapped value already exists. Mirrors
    # BRIDGE_CLIENT_SOURCE_IDS's own real match_confidence/match_method
    # fallback to composite matching when no direct id exists.
    synthetic_keys = models.JSONField(default=dict)
    # Source column names explicitly reviewed and dismissed — distinct from
    # simply unmapped. A column with no decision yet and a column someone
    # deliberately decided doesn't matter (a checksum column, an org-chart
    # role with nowhere to go) both currently just "drop from the mapping,"
    # but conflating them made it easy to lose track of which columns had
    # actually been looked at in a large real file — found live-testing a
    # 28-column Kobo distribution sheet, 2026-09-03.
    ignored_columns = models.JSONField(default=list)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="uploaded_datasets")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.country_code}/{self.program})"

    @property
    def entity_names(self) -> str:
        return ", ".join(ENTITIES[key].name for key in self.entities if key in ENTITIES)

    @property
    def valid_row_count(self) -> int:
        return self.rows.filter(is_valid=True).count()

    @property
    def invalid_row_count(self) -> int:
        return self.rows.filter(is_valid=False).count()


class UploadedRow(models.Model):
    """One row of an upload, already mapped onto glossary variable names.

    `mapped_data` is a JSONField rather than per-entity columns on purpose:
    the 8 entities have different variable sets, and modelling them
    strictly would mean 8 near-duplicate tables for no real benefit while
    the data still lives only in Wimbi. Revisit if/when the promotion ETL
    into ANALYTICS.SOURCES (v1.2+) wants a stricter shape.
    """

    dataset = models.ForeignKey(UploadedDataset, on_delete=models.CASCADE, related_name="rows")
    row_number = models.IntegerField()
    # Exactly as parsed from the file, keyed by SOURCE column name — never
    # overwritten. Re-visiting the mapping page after a first mapping pass
    # once went blank in the Sample values column, because mapped_data got
    # rewritten in place from source-column keys to variable-name keys on
    # the first save, and the sample lookup (by source column) found
    # nothing on the second visit. Splitting the two apart fixes it at the
    # root: raw_data is read-only history, mapped_data is a re-derivable
    # result recomputed from raw_data every time mapping is saved.
    raw_data = models.JSONField(default=dict)
    mapped_data = models.JSONField(default=dict)
    is_valid = models.BooleanField(default=True)
    validation_errors = models.JSONField(default=list)

    class Meta:
        ordering = ["row_number"]

    def __str__(self):
        return f"Row {self.row_number} of {self.dataset_id}"

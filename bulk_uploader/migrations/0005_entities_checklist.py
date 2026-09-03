# Replaces the single-guess "Data Type" + "entity" fields with an explicit
# multi-select "entities" checklist (2026-09-03) — see glossary.py's
# ENTITY_CHOICES docstring. Backfills each existing row's old single
# `entity` value into the new `entities` list before dropping both old
# fields, so no in-progress draft loses its funnel answer.

from django.db import migrations, models


def backfill_entities(apps, schema_editor):
    UploadedDataset = apps.get_model("bulk_uploader", "UploadedDataset")
    for dataset in UploadedDataset.objects.all():
        dataset.entities = [dataset.entity] if dataset.entity else []
        dataset.save(update_fields=["entities"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_uploader', '0004_uploadeddataset_location_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadeddataset',
            name='entities',
            field=models.JSONField(default=list),
        ),
        migrations.RunPython(backfill_entities, noop_reverse),
        migrations.RemoveField(
            model_name='uploadeddataset',
            name='entity',
        ),
        migrations.RemoveField(
            model_name='uploadeddataset',
            name='data_type',
        ),
    ]

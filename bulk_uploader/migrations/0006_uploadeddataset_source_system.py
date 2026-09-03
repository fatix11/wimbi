from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_uploader', '0005_entities_checklist'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadeddataset',
            name='source_system',
            field=models.CharField(blank=True, max_length=64),
        ),
        # "Other" dropped from LOCATION_TYPES — now a free-text escape hatch
        # like Program/Source system, not a 6th fixed choice. choices=
        # affects form/admin widgets only, no DB constraint, but Django
        # still tracks it as model state.
        migrations.AlterField(
            model_name='uploadeddataset',
            name='location_type',
            field=models.CharField(blank=True, choices=[('Nursery', 'Nursery'), ('Site', 'Site'), ('Shop', 'Shop'), ('Warehouse', 'Warehouse'), ('Online', 'Online')], max_length=16),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_uploader', '0006_uploadeddataset_source_system'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadeddataset',
            name='synthetic_keys',
            field=models.JSONField(default=dict),
        ),
    ]

# Generated by Django 4.0.7 on 2024-05-21 07:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0144_datasetviewresource_centroid_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetviewresource',
            name='vector_tiles_code_version',
            field=models.TextField(blank=True, default=''),
        ),
    ]

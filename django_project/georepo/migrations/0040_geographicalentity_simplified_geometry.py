# Generated by Django 4.0.7 on 2022-12-05 02:13

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0039_datasetview_task_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='geographicalentity',
            name='simplified_geometry',
            field=django.contrib.gis.db.models.fields.MultiPolygonField(null=True, srid=4326),
        )
    ]

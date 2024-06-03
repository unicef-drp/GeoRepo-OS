# Generated by Django 4.0.7 on 2022-12-13 23:23

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0041_dataset_trigger_view'),
    ]

    operations = [
        migrations.CreateModel(
            name='EntitySimplified',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('min_zoom_level', models.IntegerField(default=0)),
                ('max_zoom_level', models.IntegerField(default=0)),
                ('simplify_tolerance', models.FloatField(default=0)),
                ('simplified_geometry', django.contrib.gis.db.models.fields.MultiPolygonField(null=True, srid=4326)),
                ('geographical_entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='georepo.geographicalentity')),
            ],
        ),
    ]
# Generated by Django 4.0.7 on 2023-02-09 07:15

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0068_auto_20230210_0250'),
    ]

    operations = [
        migrations.AlterField(
            model_name='geographicalentity',
            name='geometry',
            field=django.contrib.gis.db.models.fields.GeometryField(null=True, srid=4326),
        ),
    ]
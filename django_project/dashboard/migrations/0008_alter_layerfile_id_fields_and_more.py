# Generated by Django 4.0.7 on 2022-10-20 05:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0007_layerfile_id_fields_layerfile_location_type_field_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='layerfile',
            name='id_fields',
            field=models.JSONField(blank=True, default=[]),
        ),
        migrations.AlterField(
            model_name='layerfile',
            name='name_fields',
            field=models.JSONField(blank=True, default=[]),
        ),
    ]
# Generated by Django 4.0.7 on 2023-01-30 08:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0059_geographicalentity_admin_level_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetadminlevelname',
            name='label',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]

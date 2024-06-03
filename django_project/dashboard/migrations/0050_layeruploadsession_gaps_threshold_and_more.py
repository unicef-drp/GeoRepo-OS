# Generated by Django 4.0.7 on 2023-05-03 04:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0049_entityuploadstatus_unique_code_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='layeruploadsession',
            name='gaps_threshold',
            field=models.FloatField(blank=True, help_text='Check for gaps smaller than (map units sqr.)', null=True),
        ),
        migrations.AddField(
            model_name='layeruploadsession',
            name='overlaps_threshold',
            field=models.FloatField(blank=True, help_text='Check for overlaps smaller than (map units sqr.)', null=True),
        ),
        migrations.AddField(
            model_name='layeruploadsession',
            name='tolerance',
            field=models.FloatField(blank=True, help_text='Tolerance for geometry checker', null=True),
        ),
    ]
# Generated by Django 4.0.7 on 2023-01-22 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0055_dataset_tiling_end_date_dataset_tiling_progress_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='styles',
            field=models.JSONField(blank=True, help_text='Styling in json', null=True),
        ),
    ]

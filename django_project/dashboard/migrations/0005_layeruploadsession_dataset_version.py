# Generated by Django 4.0.7 on 2022-10-18 07:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0021_remove_datasetversion_dataset_file_and_more'),
        ('dashboard', '0004_layeruploadsession_uploader'),
    ]

    operations = [
        migrations.AddField(
            model_name='layeruploadsession',
            name='dataset_version',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='georepo.datasetversion'),
        ),
    ]

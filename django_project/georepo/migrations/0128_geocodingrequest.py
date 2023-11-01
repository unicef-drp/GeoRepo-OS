# Generated by Django 4.0.7 on 2023-10-31 22:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('georepo', '0127_dataset_simplification_progress_num_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeocodingRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(blank=True, choices=[('PENDING', 'PENDING'), ('PROCESSING', 'PROCESSING'), ('DONE', 'DONE'), ('ERROR', 'ERROR'), ('CANCELLED', 'CANCELLED')], max_length=255, null=True)),
                ('task_id', models.CharField(max_length=256)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('submitted_on', models.DateTimeField()),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('parameters', models.TextField(blank=True, null=True)),
                ('errors', models.TextField(blank=True, null=True)),
                ('progress', models.FloatField(blank=True, null=True)),
                ('file', models.FileField(upload_to='layer_files/%Y/%m/%d/')),
                ('file_type', models.CharField(choices=[('GEOJSON', 'GEOJSON'), ('SHAPEFILE', 'SHAPEFILE'), ('GEOPACKAGE', 'GEOPACKAGE')], default='GEOJSON', max_length=100)),
                ('output_file', models.FileField(upload_to='layer_files/%Y/%m/%d/')),
                ('feature_count', models.IntegerField(blank=True, null=True)),
                ('submitted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

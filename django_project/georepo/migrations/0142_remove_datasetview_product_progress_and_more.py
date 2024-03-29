# Generated by Django 4.0.7 on 2024-02-05 00:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0141_alter_exportrequest_format'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datasetview',
            name='product_progress',
        ),
        migrations.RemoveField(
            model_name='datasetview',
            name='product_sync_status',
        ),
        migrations.RemoveField(
            model_name='datasetview',
            name='product_task_id',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='data_product_progress',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='geojson_progress',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='geojson_size',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='geojson_sync_status',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='kml_progress',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='kml_size',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='kml_sync_status',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='product_current_task',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='product_sync_status',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='product_task_id',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='product_updated_at',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='shapefile_progress',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='shapefile_size',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='shapefile_sync_status',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='topojson_progress',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='topojson_size',
        ),
        migrations.RemoveField(
            model_name='datasetviewresource',
            name='topojson_sync_status',
        ),
    ]

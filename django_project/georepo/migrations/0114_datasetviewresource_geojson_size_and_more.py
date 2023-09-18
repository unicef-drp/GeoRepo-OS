# Generated by Django 4.0.7 on 2023-09-18 12:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0113_datasetview_product_progress_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetviewresource',
            name='geojson_size',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='datasetviewresource',
            name='kml_size',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='datasetviewresource',
            name='shapefile_size',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='datasetviewresource',
            name='topojson_size',
            field=models.FloatField(default=0),
        ),
    ]

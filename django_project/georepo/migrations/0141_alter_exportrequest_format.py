# Generated by Django 4.0.7 on 2024-02-02 03:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0140_datasetviewresource_centroid_files'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exportrequest',
            name='format',
            field=models.CharField(choices=[('GEOJSON', 'GEOJSON'), ('SHAPEFILE', 'SHAPEFILE'), ('KML', 'KML'), ('TOPOJSON', 'TOPOJSON'), ('GEOPACKAGE', 'GEOPACKAGE')], max_length=255),
        ),
    ]
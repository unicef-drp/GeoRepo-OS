# Generated by Django 4.0.7 on 2023-02-08 17:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0044_layerfile_boundary_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='layerconfig',
            name='boundary_type',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
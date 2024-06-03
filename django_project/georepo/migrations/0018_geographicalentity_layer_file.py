# Generated by Django 4.0.7 on 2022-10-17 08:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_layeruploadsession_uploader'),
        ('georepo', '0017_geographicalentity_approved_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='geographicalentity',
            name='layer_file',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dashboard.layerfile'),
        ),
    ]
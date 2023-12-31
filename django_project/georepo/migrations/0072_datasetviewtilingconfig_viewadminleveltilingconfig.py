# Generated by Django 4.0.7 on 2023-02-17 02:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0071_merge_20230213_0453'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatasetViewTilingConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('zoom_level', models.IntegerField(default=0)),
                ('dataset_view', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='georepo.datasetview')),
            ],
            options={
                'ordering': ['dataset_view__id', 'zoom_level'],
            },
        ),
        migrations.CreateModel(
            name='ViewAdminLevelTilingConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.IntegerField(default=0)),
                ('simplify_tolerance', models.FloatField(default=0)),
                ('view_tiling_config', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='georepo.datasetviewtilingconfig')),
            ],
        ),
    ]

# Generated by Django 4.0.7 on 2022-12-01 08:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0038_datasetview_bbox_datasetview_description_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetview',
            name='task_id',
            field=models.CharField(blank=True, default='', max_length=256),
        ),
    ]
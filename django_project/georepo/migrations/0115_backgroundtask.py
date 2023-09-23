# Generated by Django 4.0.7 on 2023-09-23 06:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0114_datasetviewresourcelog_dataset_view'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackgroundTask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(blank=True, max_length=255, null=True)),
                ('last_update', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(blank=True, choices=[('Queued', 'Queued'), ('Running', 'Running'), ('Stopped', 'Stopped'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled'), ('Invalidated', 'Invalidated')], max_length=255, null=True)),
                ('task_id', models.CharField(max_length=256, unique=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('parameters', models.TextField(blank=True, null=True)),
                ('errors', models.TextField(blank=True, null=True)),
                ('celery_retry', models.IntegerField(default=0)),
                ('celery_last_retry_at', models.DateTimeField(blank=True, null=True)),
                ('celery_retry_reason', models.TextField(blank=True, null=True)),
            ],
        ),
    ]

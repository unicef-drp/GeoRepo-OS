# Generated by Django 4.0.7 on 2023-11-07 23:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('georepo', '0128_geocodingrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='SearchIdRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(blank=True, choices=[('PENDING', 'PENDING'), ('PROCESSING', 'PROCESSING'), ('DONE', 'DONE'), ('ERROR', 'ERROR'), ('CANCELLED', 'CANCELLED')], max_length=255, null=True)),
                ('task_id', models.CharField(blank=True, max_length=256, null=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('submitted_on', models.DateTimeField()),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('parameters', models.TextField(blank=True, null=True)),
                ('errors', models.TextField(blank=True, null=True)),
                ('progress', models.FloatField(blank=True, null=True)),
                ('last_min_poll_count', models.IntegerField(default=0)),
                ('last_min_poll_at', models.DateTimeField(blank=True, null=True)),
                ('input_id_type', models.CharField(max_length=256)),
                ('output_id_type', models.CharField(max_length=256)),
                ('input', models.JSONField(default=list)),
                ('output', models.JSONField(blank=True, default=dict, null=True)),
                ('submitted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]

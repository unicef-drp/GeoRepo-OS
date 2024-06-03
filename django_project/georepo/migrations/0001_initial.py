# Generated by Django 3.2.13 on 2022-06-07 07:17

from django.conf import settings
import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    if 'easyaudit' in settings.INSTALLED_APPS:
        dependencies = [
            ("easyaudit", "__latest__"),
        ]
    else:
        dependencies = []

    operations = [
        migrations.CreateModel(
            name='EntityType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('label', models.CharField(help_text='Examples: Country, Region, etc.', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=128)),
                ('name', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='GeographicalEntity',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('uuid', models.UUIDField(default=uuid.uuid4)),
                ('internal_code', models.CharField(blank=True, max_length=255, null=True)),
                ('level', models.IntegerField(default=0)),
                ('label', models.CharField(blank=True, max_length=255, null=True)),
                ('start_date', models.DateTimeField(blank=True, null=True)),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('is_latest', models.BooleanField(default=False)),
                ('geometry', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
                ('source', models.CharField(blank=True, max_length=255, null=True)),
                ('source_url', models.URLField(blank=True, null=True)),
                ('license', models.TextField(blank=True, null=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='georepo.geographicalentity')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='georepo.entitytype')),
            ],
        ),
        migrations.CreateModel(
            name='EntityName',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('geographical_entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='georepo.geographicalentity')),
                ('language', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='georepo.language')),
            ],
        ),
    ]
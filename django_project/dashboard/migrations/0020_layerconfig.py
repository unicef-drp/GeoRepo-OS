# Generated by Django 4.0.7 on 2022-11-09 03:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('georepo', '0031_alter_geographicalentity_parent'),
        ('dashboard', '0019_entityuploadstatus_error_report_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LayerConfig',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(default='', max_length=255)),
                ('level', models.CharField(blank=True, default='', max_length=128)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('location_type_field', models.CharField(blank=True, default='', max_length=255)),
                ('parent_id_field', models.CharField(blank=True, default='', max_length=255)),
                ('source_field', models.CharField(blank=True, default='', max_length=255)),
                ('id_fields', models.JSONField(blank=True, default=[])),
                ('name_fields', models.JSONField(blank=True, default=[])),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('dataset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='georepo.dataset')),
            ],
            options={
                'verbose_name_plural': 'Layer Configs',
                'ordering': ['created_at'],
            },
        ),
    ]
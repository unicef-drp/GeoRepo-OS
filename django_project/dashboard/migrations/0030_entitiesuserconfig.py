# Generated by Django 4.0.7 on 2022-11-29 06:21

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('georepo', '0036_entityid_georepo_ent_value_815329_idx_and_more'),
        ('dashboard', '0029_auto_20221125_0350'),
    ]

    operations = [
        migrations.CreateModel(
            name='EntitiesUserConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4)),
                ('filters', models.JSONField(blank=True, default={})),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='georepo.dataset')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

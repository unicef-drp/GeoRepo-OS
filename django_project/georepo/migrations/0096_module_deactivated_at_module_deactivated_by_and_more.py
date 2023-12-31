# Generated by Django 4.0.7 on 2023-05-26 07:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('georepo', '0095_merge_20230525_0701'),
    ]

    operations = [
        migrations.AddField(
            model_name='module',
            name='deactivated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='module',
            name='deactivated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deactivated_module', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='module',
            name='is_active',
            field=models.BooleanField(default=True, help_text='To enable/disable module'),
        ),
    ]

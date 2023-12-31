# Generated by Django 4.0.7 on 2022-10-20 02:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('georepo', '0022_remove_dataset_dataset_group_dataset_module'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='created_at',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name='dataset',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='entitytype',
            name='label_plural',
            field=models.CharField(blank=True, help_text='Examples: Countries, Regions, etc.', max_length=255, null=True),
        ),
    ]

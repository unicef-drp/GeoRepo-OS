# Generated by Django 4.0.7 on 2023-05-25 04:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('georepo', '0093_alter_datasetview_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='deprecated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dataset',
            name='deprecated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deprecated_dataset', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='dataset',
            name='is_active',
            field=models.BooleanField(default=True, help_text='To deprecate/activate dataset'),
        ),
    ]
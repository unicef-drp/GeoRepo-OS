# Generated by Django 4.0.7 on 2023-01-30 08:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0059_module_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='short_code',
            field=models.CharField(blank=True, default='', max_length=16),
        ),
    ]

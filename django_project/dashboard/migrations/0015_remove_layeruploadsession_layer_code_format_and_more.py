# Generated by Django 4.0.7 on 2022-10-27 03:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0014_layeruploadsession_last_step'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='layeruploadsession',
            name='layer_code_format',
        ),
        migrations.RemoveField(
            model_name='layeruploadsession',
            name='layer_name_format',
        ),
    ]
# Generated by Django 4.0.7 on 2022-11-02 09:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0017_entityuploadstatus_error_summaries'),
    ]

    operations = [
        migrations.RenameField(
            model_name='entityuploadstatus',
            old_name='error_summaries',
            new_name='summaries',
        ),
    ]
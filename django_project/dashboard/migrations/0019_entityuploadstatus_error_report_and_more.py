# Generated by Django 4.0.7 on 2022-11-02 10:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0018_rename_error_summaries_entityuploadstatus_summaries'),
    ]

    operations = [
        migrations.AddField(
            model_name='entityuploadstatus',
            name='error_report',
            field=models.FileField(null=True, upload_to='error_reports'),
        ),
        migrations.AlterField(
            model_name='entityuploadstatus',
            name='summaries',
            field=models.JSONField(blank=True, max_length=1024, null=True),
        ),
    ]
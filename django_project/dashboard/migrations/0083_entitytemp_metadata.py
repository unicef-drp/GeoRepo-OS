# Generated by Django 4.0.7 on 2023-10-30 08:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0082_alter_entityuploadstatus_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='entitytemp',
            name='metadata',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]
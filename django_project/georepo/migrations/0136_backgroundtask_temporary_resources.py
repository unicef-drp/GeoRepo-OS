# Generated by Django 4.0.7 on 2024-01-22 22:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0135_exportrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='backgroundtask',
            name='temporary_resources',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]

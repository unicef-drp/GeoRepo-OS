# Generated by Django 4.0.7 on 2023-07-03 13:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_merge_20230512_0328'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitepreferences',
            name='default_admin_emails',
            field=models.JSONField(blank=True, default=[]),
        ),
    ]
# Generated by Django 4.0.7 on 2024-04-07 19:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_sitepreferences_blob_storage_domain_whitelist'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitepreferences',
            name='login_help_text',
            field=models.TextField(default='', help_text='Help text to show in login page.'),
        ),
    ]

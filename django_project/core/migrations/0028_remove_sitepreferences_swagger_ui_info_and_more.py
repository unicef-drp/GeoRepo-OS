# Generated by Django 4.0.7 on 2023-09-14 02:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_sitepreferences_swagger_ui_info'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sitepreferences',
            name='swagger_ui_info',
        ),
        migrations.AddField(
            model_name='sitepreferences',
            name='swagger_api_documentation_link',
            field=models.TextField(default='', help_text='Documentation Link shown at the top of Swagger UI.'),
        ),
    ]

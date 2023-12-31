# Generated by Django 4.0.7 on 2023-08-01 06:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0059_alter_notification_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='batchreview',
            name='processed_ids',
            field=models.JSONField(blank=True, default=list, help_text='List of entity uploads that has been processed', null=True),
        ),
        migrations.AlterField(
            model_name='batchreview',
            name='upload_ids',
            field=models.JSONField(blank=True, default=list, help_text='List of entity uploads', null=True),
        ),
        migrations.AlterField(
            model_name='entitiesuserconfig',
            name='filters',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='entityuploadstatus',
            name='admin_level_names',
            field=models.JSONField(blank=True, default=dict, help_text='Name of admin levels', null=True),
        ),
        migrations.AlterField(
            model_name='layerconfig',
            name='id_fields',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='layerconfig',
            name='name_fields',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='layerfile',
            name='id_fields',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='layerfile',
            name='name_fields',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='notification',
            name='payload',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]

# Generated by Django 4.0.7 on 2023-01-25 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0056_alter_dataset_styles'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetview',
            name='default_ancestor_code',
            field=models.CharField(blank=True, help_text='If not null, then default view is per adm level 0', max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='datasetview',
            name='default_type',
            field=models.CharField(blank=True, choices=[('LATEST', 'Is Latest'), ('ALL', 'All Versions')], help_text='If not null, then this is default view', max_length=256, null=True),
        ),
    ]
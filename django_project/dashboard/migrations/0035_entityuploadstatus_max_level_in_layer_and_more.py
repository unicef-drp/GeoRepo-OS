# Generated by Django 4.0.7 on 2023-01-03 05:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0034_boundarycomparison_is_parent_rematched'),
    ]

    operations = [
        migrations.AddField(
            model_name='entityuploadstatus',
            name='max_level_in_layer',
            field=models.CharField(blank=True, default='', help_text='Max level for a country in layer file', max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='entityuploadstatus',
            name='max_level',
            field=models.CharField(blank=True, default='', help_text='Selected max level to be imported', max_length=128, null=True),
        ),
    ]

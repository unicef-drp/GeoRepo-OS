# Generated by Django 4.0.7 on 2022-12-07 03:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0031_entityuploadstatus_revised_entity_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='entityuploadstatus',
            name='max_level',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
    ]
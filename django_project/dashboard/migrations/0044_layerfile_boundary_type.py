# Generated by Django 4.0.7 on 2023-02-08 16:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0043_merge_20230127_0611'),
    ]

    operations = [
        migrations.AddField(
            model_name='layerfile',
            name='boundary_type',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]

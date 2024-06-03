# Generated by Django 4.0.7 on 2023-04-12 13:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0091_init_geosight_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='georeporole',
            name='type',
            field=models.CharField(blank=True, choices=[('Creator', 'Creator'), ('Viewer', 'Viewer')], default='Viewer', max_length=255, null=True),
        ),
    ]
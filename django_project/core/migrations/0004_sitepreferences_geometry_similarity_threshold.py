# Generated by Django 4.0.7 on 2022-12-29 08:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_sitepreferences_search_simplify_tolerance'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitepreferences',
            name='geometry_similarity_threshold',
            field=models.FloatField(blank=True, default=-1, help_text='Threshold for geometry similarity in boundary matching', null=True),
        ),
    ]
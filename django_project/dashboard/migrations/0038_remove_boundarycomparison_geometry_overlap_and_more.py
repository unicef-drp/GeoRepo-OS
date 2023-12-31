# Generated by Django 4.0.7 on 2023-01-18 06:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0037_maintenance'),
    ]

    operations = [
        migrations.RenameField(
            model_name='boundarycomparison',
            old_name='geometry_overlap',
            new_name='geometry_overlap_new',
        ),
        migrations.AlterField(
            model_name='boundarycomparison',
            name='geometry_overlap_new',
            field=models.FloatField(blank=True, help_text='Overlap new area covered by old area', null=True),
        ),
        migrations.AddField(
            model_name='boundarycomparison',
            name='geometry_overlap_old',
            field=models.FloatField(blank=True, help_text='Overlap old area covered by new area', null=True),
        ),
        migrations.AddField(
            model_name='boundarycomparison',
            name='is_same_entity',
            field=models.BooleanField(default=True, help_text='Same entity concept, True if both similarities are above thresholds. This can be manually changed by end user'),
        ),
    ]

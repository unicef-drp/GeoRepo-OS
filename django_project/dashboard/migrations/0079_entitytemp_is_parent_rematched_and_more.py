# Generated by Django 4.0.7 on 2023-09-28 04:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0078_entitytemp_dashboard_e_level_47c2ac_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='entitytemp',
            name='is_parent_rematched',
            field=models.BooleanField(default=False, help_text='True if rematched parent has different default code'),
        ),
        migrations.AddField(
            model_name='entitytemp',
            name='overlap_percentage',
            field=models.FloatField(blank=True, default=0, null=True),
        ),
    ]
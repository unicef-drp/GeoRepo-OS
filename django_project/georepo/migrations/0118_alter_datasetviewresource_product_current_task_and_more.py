# Generated by Django 4.0.7 on 2023-09-26 05:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0117_datasetview_simplification_current_task'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetviewresource',
            name='product_current_task',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_current_view', to='georepo.backgroundtask'),
        ),
        migrations.AlterField(
            model_name='datasetviewresource',
            name='tiling_current_task',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tiling_current_view', to='georepo.backgroundtask'),
        ),
    ]

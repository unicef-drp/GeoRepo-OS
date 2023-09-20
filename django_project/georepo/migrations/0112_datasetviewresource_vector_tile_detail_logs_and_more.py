# Generated by Django 4.0.7 on 2023-09-20 19:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0111_entitysimplified_dataset_view'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetviewresource',
            name='vector_tile_detail_logs',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AlterField(
            model_name='datasetview',
            name='status',
            field=models.CharField(choices=[('PE', 'Pending'), ('PR', 'Processing'), ('DO', 'Done'), ('ER', 'Error'), ('EM', 'Empty')], default='PE', max_length=2),
        ),
        migrations.AlterField(
            model_name='datasetviewresource',
            name='status',
            field=models.CharField(choices=[('PE', 'Pending'), ('PR', 'Processing'), ('DO', 'Done'), ('ER', 'Error'), ('EM', 'Empty')], default='PE', max_length=2),
        ),
    ]

# Generated by Django 4.0.7 on 2022-11-01 03:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0015_remove_layeruploadsession_layer_code_format_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entityuploadstatus',
            name='status',
            field=models.CharField(blank=True, choices=[('Started', 'Started'), ('Valid', 'Valid'), ('Error', 'Error'), ('Processing', 'Processing'), ('Reviewing', 'Reviewing')], default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='layeruploadsession',
            name='status',
            field=models.CharField(choices=[('Done', 'Done'), ('Validating', 'Validating'), ('Pending', 'Pending'), ('Canceled', 'Canceled'), ('Error', 'Error'), ('Processing', 'Processing'), ('Reviewing', 'Reviewing')], max_length=128),
        ),
    ]
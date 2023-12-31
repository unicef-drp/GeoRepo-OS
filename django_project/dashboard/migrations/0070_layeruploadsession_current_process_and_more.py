# Generated by Django 4.0.7 on 2023-09-19 16:54

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0069_layeruploadsessionactionlog_data_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='layeruploadsession',
            name='current_process',
            field=models.CharField(blank=True, choices=[('Preparing for Validation', 'Preparing for Validation'), ('Processing Countries Selection', 'Processing Countries Selection'), ('Countries Validation', 'Countries Validation'), ('Processing selected countries for review', 'Processing selected countries for review'), ('Preparing for Review', 'Preparing for Review')], max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='layeruploadsession',
            name='current_process_uuid',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='layeruploadsessionactionlog',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]

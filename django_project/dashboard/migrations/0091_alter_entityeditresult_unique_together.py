# Generated by Django 4.0.7 on 2024-05-20 10:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0090_entityeditresult'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='entityeditresult',
            unique_together={('batch_edit', 'row_idx')},
        ),
    ]

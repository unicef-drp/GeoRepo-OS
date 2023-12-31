# Generated by Django 4.0.7 on 2023-10-05 04:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0079_entitytemp_is_parent_rematched_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entityuploadstatus',
            name='status',
            field=models.CharField(blank=True, choices=[('Started', 'Started'), ('Valid', 'Valid'), ('Error', 'Error'), ('Processing', 'Processing'), ('Reviewing', 'Reviewing'), ('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Processing_Approval', 'Processing_Approval'), ('Error Processing', 'Error Processing')], default='', max_length=100),
        ),
    ]

from django.db import models
from django.utils import timezone


class TempUsage(models.Model):

    report_file = models.FileField(
        upload_to='reports/%Y/%m/%d/'
    )

    report_date = models.DateTimeField(default=timezone.now)

    total_size = models.FloatField(
        default=0
    )

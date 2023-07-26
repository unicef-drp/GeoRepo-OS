from django.db import models


class BoundaryType(models.Model):

    dataset = models.ForeignKey(
        'georepo.Dataset',
        on_delete=models.CASCADE,
        null=False,
        blank=False
    )

    type = models.ForeignKey(
        'georepo.EntityType',
        on_delete=models.CASCADE,
        null=False,
        blank=False
    )

    value = models.CharField(
        default='',
        blank=False,
        null=False,
        max_length=255
    )

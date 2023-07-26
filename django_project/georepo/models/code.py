from django.db import models


class CodeCL(models.Model):
    name = models.CharField(
        max_length=128,
        blank=False,
        null=False
    )

    def __str__(self):
        return self.name


class EntityCode(models.Model):
    entity = models.ForeignKey(
        'georepo.GeographicalEntity',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    code_cl = models.ForeignKey(
        'georepo.CodeCL',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    code = models.CharField(
        max_length=128,
        null=False,
        blank=False
    )

    def __str__(self):
        return self.code

from django.db import models


class PrivacyLevel(models.Model):

    privacy_level = models.PositiveIntegerField(
        unique=True
    )

    label = models.CharField(
        max_length=30
    )

    def __str__(self) -> str:
        return f'{self.privacy_level} - {self.label}'

from django.db import models
from django.conf import settings

NOTIF_TYPE_BOUNDARY_MATCHING = 'BOUNDARY_MATCHING'
NOTIF_TYPE_LAYER_VALIDATION = 'LAYER_VALIDATION'
NOTIF_TYPE_GENERATE_TILES = 'GENERATE_TILES'
NOTIF_TYPE_PARENT_MATCHING = 'PARENT_MATCHING'
NOTIF_TYPE_BATCH_REVIEW = 'BATCH_REVIEW'
NOTIF_TYPE_BATCH_ENTITY_EDIT = 'BATCH_ENTITY_EDIT'
NOTIF_TYPE_DATASET_VIEW_EXPORTER = 'DATASET_VIEW_EXPORTER'


class Notification(models.Model):

    NOTIF_TYPE_CHOICES = (
        (NOTIF_TYPE_BOUNDARY_MATCHING,
            NOTIF_TYPE_BOUNDARY_MATCHING),
        (NOTIF_TYPE_LAYER_VALIDATION, NOTIF_TYPE_LAYER_VALIDATION),
        (NOTIF_TYPE_GENERATE_TILES, NOTIF_TYPE_GENERATE_TILES),
        (NOTIF_TYPE_PARENT_MATCHING, NOTIF_TYPE_PARENT_MATCHING),
        (NOTIF_TYPE_BATCH_REVIEW, NOTIF_TYPE_BATCH_REVIEW),
        (NOTIF_TYPE_BATCH_ENTITY_EDIT, NOTIF_TYPE_BATCH_ENTITY_EDIT),
        (NOTIF_TYPE_DATASET_VIEW_EXPORTER, NOTIF_TYPE_DATASET_VIEW_EXPORTER)
    )

    type = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        choices=NOTIF_TYPE_CHOICES
    )

    message = models.CharField(
        max_length=255,
        blank=False,
        null=False
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=False,
        null=False
    )

    payload = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name_plural = 'Notifications'
        ordering = ['created_at']

    def __str__(self):
        return self.message

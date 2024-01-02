from django.db import models
from georepo.models.base_task_request import BaseTaskRequest


class BatchEntityEdit(BaseTaskRequest):

    dataset = models.ForeignKey(
        'georepo.Dataset',
        on_delete=models.CASCADE
    )

    input_file = models.FileField(
        upload_to='batch_entity_edit/input/%Y/%m/%d/',
        null=True,
        blank=True
    )

    output_file = models.FileField(
        upload_to='batch_entity_edit/output/%Y/%m/%d/',
        null=True,
        blank=True
    )

    id_fields = models.JSONField(
        default=list,
        blank=True
    )

    name_fields = models.JSONField(
        default=list,
        blank=True
    )

    ucode_field = models.CharField(
        default='',
        blank=True,
        max_length=512
    )

    error_notes = models.TextField(
        blank=True,
        null=True
    )

    success_notes = models.TextField(
        blank=True,
        null=True
    )

    total_count = models.IntegerField(
        default=0
    )

    success_count = models.IntegerField(
        default=0
    )

    error_count = models.IntegerField(
        default=0
    )

    headers = models.JSONField(
        default=list,
        blank=True
    )

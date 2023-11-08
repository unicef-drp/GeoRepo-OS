from django.db import models
from georepo.models.base_task_request import BaseTaskRequest


class SearchIdRequest(BaseTaskRequest):

    input_id_type = models.CharField(
        max_length=256
    )

    output_id_type = models.CharField(
        max_length=256
    )

    input = models.JSONField(
        default=list
    )

    output = models.JSONField(
        default=dict,
        null=True,
        blank=True
    )

    def __str__(self):
        return str(self.uuid)

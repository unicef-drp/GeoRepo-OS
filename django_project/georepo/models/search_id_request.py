from django.db import models
from georepo.models.base_task_request import BaseTaskRequest


class SearchIdRequest(BaseTaskRequest):

    input_id_type = models.CharField(
        max_length=256
    )

    output_id_type = models.CharField(
        max_length=256,
        null=True,
        blank=True
    )

    input = models.JSONField(
        default=list
    )

    output_file = models.FileField(
        upload_to='search_id/%Y/%m/%d/',
        null=True,
        blank=True
    )

    def __str__(self):
        return str(self.uuid)

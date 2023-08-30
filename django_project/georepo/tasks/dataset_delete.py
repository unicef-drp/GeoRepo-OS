from celery import shared_task

from georepo.models.dataset import Dataset


@shared_task(name="dataset_delete")
def dataset_delete(dataset_ids):
    Dataset.objects.filter(id__in=dataset_ids).delete()

from celery import shared_task

from georepo.models.dataset import Dataset


@shared_task(name="dataset_delete")
def dataset_delete(dataset_ids):
    from dashboard.models.layer_upload_session import LayerUploadSession
    from dashboard.tasks.upload import delete_layer_upload_session
    upload_sessions = LayerUploadSession.objects.filter(
        dataset_id__in=dataset_ids
    )
    for upload_session in upload_sessions:
        delete_layer_upload_session(upload_session.id)
    Dataset.objects.filter(id__in=dataset_ids).delete()

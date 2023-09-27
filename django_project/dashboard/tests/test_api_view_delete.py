import mock
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIRequestFactory

from dashboard.api_views.dataset import (
    DeleteDataset
)
from georepo.models import (
    GeographicalEntity
)
from dashboard.models import (
    LayerFile,
    PENDING,
    DONE
)
from dashboard.tests.model_factories import LayerFileF, LayerUploadSessionF
from georepo.tests.model_factories import (
    UserF, DatasetF, GeographicalEntityF, ModuleF
)
from dashboard.api_views.upload_session import (
    DeleteUploadSession
)
from dashboard.tasks.upload import delete_layer_upload_session


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_process(*args, **kwargs):
    return DummyTask('1')


class TestDeleteApiViews(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(
            module=self.module,
            generate_adm0_default_views=True
        )
        self.superuser = UserF.create(is_superuser=True)

    @mock.patch(
        'dashboard.api_views.dataset.dataset_delete.delay',
        mock.Mock(side_effect=mocked_process)
    )
    def test_delete_dataset(self):
        # Test no permission
        user = UserF.create()
        dataset = DatasetF.create()
        request = self.factory.post(
            reverse('delete-dataset', kwargs={
                'id': dataset.id
            }), {},
            format='json'
        )
        request.user = user
        delete_dataset_view = DeleteDataset.as_view()
        response = delete_dataset_view(request, **{
            'id': dataset.id
        })
        self.assertEqual(response.status_code, 403)

        # Test creator deleting dataset
        dataset_1 = DatasetF.create(created_by=user)
        request = self.factory.post(
            reverse('delete-dataset', kwargs={
                'id': dataset_1.id
            }), {},
            format='json'
        )
        request.user = user
        delete_dataset_view = DeleteDataset.as_view()
        response = delete_dataset_view(request, **{
            'id': dataset_1.id
        })
        self.assertEqual(response.status_code, 200)

        # Test superuser deleting dataset
        superuser = UserF.create(is_superuser=True)
        dataset_2 = DatasetF.create(created_by=superuser)
        request = self.factory.post(
            reverse('delete-dataset', kwargs={
                'id': dataset_2.id
            }), {},
            format='json'
        )
        request.user = superuser
        delete_dataset_view = DeleteDataset.as_view()
        response = delete_dataset_view(request, **{
            'id': dataset_2.id
        })
        self.assertEqual(response.status_code, 200)

    @mock.patch(
        'dashboard.api_views.upload_session.'
        'delete_layer_upload_session.delay',
        mock.Mock(side_effect=mocked_process)
    )
    def test_delete_upload_session(self):
        dataset = DatasetF.create()
        user_1 = UserF.create()
        user_2 = UserF.create()
        upload_session = LayerUploadSessionF.create(
            dataset=dataset,
            uploader=user_1
        )
        layer_file = LayerFileF.create(
            layer_upload_session=upload_session,
            uploader=user_1
        )
        entity = GeographicalEntityF.create(
            dataset=dataset,
            layer_file=layer_file
        )
        kwargs = {
            'id': upload_session.id
        }
        request = self.factory.post(
            reverse('delete-upload-session', kwargs=kwargs), {},
            format='json'
        )
        # not permitted
        request.user = user_2
        query_view = DeleteUploadSession.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 403)
        # status cannot be deleted
        upload_session.status = DONE
        upload_session.save()
        request.user = user_1
        query_view = DeleteUploadSession.as_view()
        response = query_view(request, **kwargs)
        self.assertEqual(response.status_code, 400)
        # can delete, and the entity is deleted too
        upload_session.status = PENDING
        upload_session.save()
        request.user = user_1
        query_view = DeleteUploadSession.as_view()
        response = query_view(request, **kwargs)
        delete_layer_upload_session(upload_session.id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LayerFile.objects.filter(
            id=layer_file.id
        ).exists())
        self.assertFalse(GeographicalEntity.objects.filter(
            id=entity.id
        ).exists())

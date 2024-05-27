import mock
import json
from django.test import TestCase
from django.urls import reverse

from dateutil.parser import isoparse
from django.contrib.gis.geos import GEOSGeometry
from rest_framework.test import APIRequestFactory

from dashboard.api_views.dataset import (
    DeleteDataset
)
from georepo.models import (
    GeographicalEntity, IdType, Dataset, EntityId, EntityName
)
from dashboard.models import (
    LayerFile,
    PENDING,
    DONE
)
from georepo.utils import absolute_path
from dashboard.tests.model_factories import LayerFileF, LayerUploadSessionF
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, EntityIdF,
    EntityNameF, LanguageF, UserF, ModuleF
)
from dashboard.api_views.upload_session import (
    DeleteUploadSession
)
from dashboard.tasks.upload import delete_layer_upload_session
from georepo.tasks.dataset_delete import dataset_delete


class DummyTask:
    def __init__(self, id):
        self.id = id


def mocked_process(*args, **kwargs):
    return DummyTask('1')


class TestDeleteApiViews(TestCase):

    def setUp(self) -> None:
        self.enLang = LanguageF.create(
            code='EN',
            name='English'
        )
        self.esLang = LanguageF.create(
            code='ES',
            name='Spanist'
        )
        self.pCode = IdType.objects.create(name='PCode')
        self.iso3cd = IdType.objects.create(name='ISO3DC')
        self.entity_type = EntityTypeF.create(label='Country')
        self.factory = APIRequestFactory()
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(
            module=self.module,
            generate_adm0_default_views=True
        )
        self.superuser = UserF.create(is_superuser=True)
        # add entities to self.dataset
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.geographical_entity = GeographicalEntityF.create(
                dataset=self.dataset,
                type=self.entity_type,
                is_validated=True,
                is_approved=True,
                is_latest=True,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK',
                revision_number=1,
                label='Pakistan',
                unique_code='PAK',
                start_date=isoparse('2023-01-01T06:16:13Z'),
                concept_ucode='#PAK_1'
            )
            self.geographical_entity_code_1 = EntityIdF.create(
                code=self.pCode,
                geographical_entity=self.geographical_entity,
                default=True,
                value=self.geographical_entity.internal_code
            )
            self.geographical_entity_code_2 = EntityIdF.create(
                code=self.iso3cd,
                geographical_entity=self.geographical_entity,
                default=False,
                value='some-code'
            )
            self.geographical_entity_name_1 = EntityNameF.create(
                geographical_entity=self.geographical_entity,
                name=self.geographical_entity.label,
                language=self.enLang,
                idx=0
            )
            self.geographical_entity_name_2 = EntityNameF.create(
                geographical_entity=self.geographical_entity,
                name='only paktang',
                default=False,
                language=self.esLang,
                idx=1
            )

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


    def test_task_dataset_delete(self):
        # create new dataset
        new_ds = DatasetF.create(
            module=self.module,
            generate_adm0_default_views=True
        )
        # add new entities
        entity = GeographicalEntityF.create(
            dataset=new_ds,
            type=self.entity_type,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='PAK',
            revision_number=1,
            label='Pakistan',
            unique_code='PAK',
            start_date=isoparse('2023-01-01T06:16:13Z'),
            concept_ucode='#PAK_1'
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=entity,
            default=True,
            value=entity.internal_code
        )
        EntityNameF.create(
            geographical_entity=entity,
            name=entity.label,
            language=self.enLang,
            idx=0
        )
        dataset_delete([new_ds.id])
        # assert ds is removed
        self.assertFalse(Dataset.objects.filter(id=new_ds.id).exists())
        self.assertFalse(
            GeographicalEntity.objects.filter(dataset_id=new_ds.id).exists())
        self.assertFalse(
            EntityId.objects.filter(
                geographical_entity__dataset_id=new_ds.id).exists())
        self.assertFalse(
            EntityName.objects.filter(
                geographical_entity__dataset_id=new_ds.id).exists())
        # assert entities in self.dataset still exist
        self.assertTrue(Dataset.objects.filter(id=self.dataset.id).exists())
        self.assertTrue(
            GeographicalEntity.objects.filter(
                dataset_id=self.dataset.id).exists())
        self.assertTrue(
            EntityId.objects.filter(
                geographical_entity__dataset_id=self.dataset.id).exists())
        self.assertTrue(
            EntityName.objects.filter(
                geographical_entity__dataset_id=self.dataset.id).exists())

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

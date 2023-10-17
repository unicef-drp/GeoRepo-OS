__author__ = 'zakki@kartoza.com'
__date__ = '02/08/23'
__copyright__ = ('Copyright 2023, Unicef')

import json

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from django.contrib.gis.geos import GEOSGeometry

from dashboard.api_views.reviews import ReviewFilterValue
from dashboard.models.entity_upload import APPROVED, REVIEWING, REJECTED
from dashboard.tests.model_factories import (
    EntityUploadF, LayerUploadSessionF
)
from georepo.tests.model_factories import (
    UserF, DatasetF,
    ModuleF, GeographicalEntityF
)
from georepo.utils import absolute_path


class TestReviewFilterValue(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.superuser = UserF.create(is_superuser=True)
        self.creator = UserF.create()
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        dataset = DatasetF.create(
            module=self.module,
            generate_adm0_default_views=True
        )
        self.upload_session = LayerUploadSessionF.create(
            dataset=dataset,
            uploader=self.creator,
            source='TEST'
        )
        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.entity_1 = GeographicalEntityF.create(
                revision_number=1,
                level=0,
                dataset=dataset,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK',
                label='Pakistan'
            )
            self.entity_2 = GeographicalEntityF.create(
                revision_number=2,
                level=1,
                dataset=dataset,
                geometry=GEOSGeometry(geom_str),
                internal_code='PAK01',
                label='Islamabad'
            )
        self.entity_upload_status_1 = EntityUploadF.create(
            upload_session=self.upload_session,
            status=REVIEWING,
            revised_geographical_entity=self.entity_1
        )
        EntityUploadF.create(
            upload_session=self.upload_session,
            status=REJECTED,
        )
        self.entity_upload_status_3 = EntityUploadF.create(
            upload_session=self.upload_session,
            status=APPROVED,
            revised_geographical_entity=self.entity_2
        )

    def test_list_level_0_entity(self):
        request = self.factory.get(
            reverse(
                'review-filter-value',
                kwargs={'criteria': 'level_0_entity'}
            )
        )
        request.user = self.superuser
        list_view = ReviewFilterValue.as_view()
        response = list_view(request, 'level_0_entity')
        self.assertEquals(
            response.data,
            [
                self.entity_2.label,
                self.entity_1.label,
            ]
        )

    def test_list_upload(self):
        request = self.factory.get(
            reverse('review-filter-value', kwargs={'criteria': 'upload'})
        )
        request.user = self.superuser
        list_view = ReviewFilterValue.as_view()
        response = list_view(request, 'upload')
        self.assertEquals(response.data, [self.upload_session.id])

    def test_list_revision(self):
        request = self.factory.get(
            reverse('review-filter-value', kwargs={'criteria': 'revision'})
        )
        request.user = self.superuser
        list_view = ReviewFilterValue.as_view()
        response = list_view(request, 'revision')
        self.assertEquals(
            response.data,
            [
                self.entity_1.revision_number,
                self.entity_2.revision_number
            ]
        )

    def test_list_dataset(self):
        request = self.factory.get(
            reverse('review-filter-value', kwargs={'criteria': 'dataset'})
        )
        request.user = self.superuser
        list_view = ReviewFilterValue.as_view()
        response = list_view(request, 'dataset')
        self.assertIn(self.upload_session.dataset.label, response.data)

    def test_list_status(self):
        request = self.factory.get(
            reverse('review-filter-value', kwargs={'criteria': 'status'})
        )
        request.user = self.superuser
        list_view = ReviewFilterValue.as_view()
        response = list_view(request, 'status')
        self.assertEquals(
            response.data,
            [APPROVED, 'Processing', 'Ready for Review']
        )

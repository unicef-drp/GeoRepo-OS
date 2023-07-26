from collections import OrderedDict
from uuid import UUID

import mock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from georepo.api_views.dataset import DatasetList
from georepo.tests.model_factories import (
    GeographicalEntityF, DatasetF, UserF
)


def mocked_cache_get(self, *args, **kwargs):
    return OrderedDict(
        [('name', 'entity 0'),
         ('uuid', UUID('4685e7fe-5996-48aa-9e56-98820f53a7b2'))]
    )


class TestApiCache(TestCase):

    def setUp(self) -> None:
        self.view = DatasetList.as_view()
        self.dataset = DatasetF.create()
        self.entity = GeographicalEntityF.create(
            label='entity 0',
            dataset=self.dataset
        )
        self.factory = APIRequestFactory()
        self.superuser = UserF.create(is_superuser=True)

    @mock.patch('django.core.cache.cache.get',
                mock.Mock(side_effect=mocked_cache_get))
    def test_get_cache(self):
        kwargs = {
            'uuid': self.dataset.module.uuid
        }
        request = self.factory.get(
            reverse('v1:dataset-list', kwargs=kwargs)
        )
        request.user = self.superuser
        response = self.view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.entity.label, 'entity 0')

    def test_get_without_cache(self):
        kwargs = {
            'uuid': self.dataset.module.uuid
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-list',
                kwargs=kwargs
            ) + '?cached=False'
        )
        request.user = self.superuser
        response = self.view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertIn('dataset', response.data['results'][0].get('name'))
        self.assertNotIn('short_code', response.data['results'][0])

    def test_dataset_list_module_disabled(self):
        dataset = DatasetF.create()
        dataset.module.is_active = False
        dataset.module.save()
        kwargs = {
            'uuid': dataset.module.uuid
        }
        request = self.factory.get(
            reverse(
                'v1:dataset-list',
                kwargs=kwargs
            ) + '?cached=False'
        )
        request.user = self.superuser
        response = self.view(request, **kwargs)
        self.assertEqual(response.status_code, 404)

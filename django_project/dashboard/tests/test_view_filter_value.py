__author__ = 'zakki@kartoza.com'
__date__ = '31/07/23'
__copyright__ = ('Copyright 2023, Unicef')

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from dashboard.api_views.views import (
    ViewFilterValue
)
from georepo.tests.model_factories import (
    UserF, DatasetF, DatasetViewF, ModuleF
)
from georepo.utils.permission import (
    grant_dataset_manager
)


class TestViewFilterValue(TestCase):

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
        self.creator = UserF.create()
        self.dataset_view_1 = DatasetViewF.create(
            created_by=self.creator
        )
        grant_dataset_manager(self.dataset_view_1.dataset, self.creator)

    def test_list_dataset(self):
        request = self.factory.get(
            reverse('view-filter-value', kwargs={'criteria': 'dataset'})
        )
        request.user = self.superuser
        list_view = ViewFilterValue.as_view()
        response = list_view(request, 'dataset')
        self.assertTrue(response.data, [self.dataset_view_1.dataset])

    def test_list_mode(self):
        request = self.factory.get(
            reverse('view-filter-value', kwargs={'criteria': 'mode'})
        )
        request.user = self.superuser
        list_view = ViewFilterValue.as_view()
        response = list_view(request, 'mode')
        self.assertTrue(response.data, ['Static', 'Dynamic'])

    def test_list_is_default(self):
        request = self.factory.get(
            reverse('view-filter-value', kwargs={'criteria': 'is_default'})
        )
        request.user = self.superuser
        list_view = ViewFilterValue.as_view()
        response = list_view(request, 'is_default')
        self.assertTrue(response.data, ['Yes', 'No'])

    def test_list_max_privacy(self):
        request = self.factory.get(
            reverse('view-filter-value', kwargs={'criteria': 'max_privacy'})
        )
        request.user = self.superuser
        list_view = ViewFilterValue.as_view()
        response = list_view(request, 'max_privacy')
        self.assertTrue(response.data, [self.dataset_view_1.max_privacy_level])

    def test_list_min_privacy(self):
        request = self.factory.get(
            reverse('view-filter-value', kwargs={'criteria': 'min_privacy'})
        )
        request.user = self.superuser
        list_view = ViewFilterValue.as_view()
        response = list_view(request, 'min_privacy')
        self.assertTrue(response.data, [self.dataset_view_1.max_privacy_level])

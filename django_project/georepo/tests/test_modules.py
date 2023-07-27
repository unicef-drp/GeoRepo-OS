from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from georepo.api_views.module import ModuleList
from georepo.tests.model_factories import (
    ModuleF, UserF
)


class TestAPIModule(TestCase):

    def setUp(self) -> None:
        self.view = ModuleList.as_view()
        self.module = ModuleF.create(
            name='ABC'
        )
        self.module_2 = ModuleF.create(
            name='Module A',
            description='Module A desc'
        )
        self.factory = APIRequestFactory()
        self.superuser = UserF.create(is_superuser=True)

    def test_get_module_list(self):
        request = self.factory.get(
            reverse('v1:module-list')
        )
        request.user = self.superuser
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 4)
        moduleABC = (
            [x for x in response.data['results'] if x['name'] == 'ABC']
        )
        self.assertTrue(moduleABC)
        self.assertNotIn('description', moduleABC[0])
        moduleA = (
            [x for x in response.data['results'] if x['name'] == 'Module A']
        )
        self.assertTrue(moduleA)
        self.assertEqual(moduleA[0]['description'], self.module_2.description)
        # update module_2 to inactive
        self.module_2.is_active = False
        self.module_2.save()
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)
        moduleA = (
            [x for x in response.data['results'] if x['name'] == 'Module A']
        )
        self.assertFalse(moduleA)

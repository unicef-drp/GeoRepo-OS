from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from dashboard.api_views.views import SQLColumnsTablesList, QueryViewCheck,\
    QueryViewPreview
from georepo.tests.model_factories import (
    UserF, GeographicalEntityF, DatasetF
)
from dashboard.models.entities_user_config import EntitiesUserConfig


class TestSqlViews(TransactionTestCase):
    def setUp(self) -> None:
        self.factory = APIRequestFactory()

    def test_query_check(self):
        query_string = (
            'select * from georepo_geographicalentity WHERE label=\'test\''
        )
        GeographicalEntityF.create()
        user = UserF.create()
        dataset = DatasetF.create()
        request = self.factory.post(
            reverse('query-view-check'), {
                'query_string': query_string,
                'dataset': dataset.id
            }
        )
        request.user = user
        query_view = QueryViewCheck.as_view()
        response = query_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['valid'], True)

        query_string = (
            'select * geographicalentity'
        )
        request = self.factory.post(
            reverse('query-view-check'), {
                'query_string': query_string,
                'dataset': dataset.id
            }
        )
        request.user = user
        query_view = QueryViewCheck.as_view()
        response = query_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['valid'], False)

        query_string = 'DROP TABLE georepo_geographicalentity'
        request = self.factory.post(
            reverse('query-view-check'), {
                'query_string': query_string,
                'dataset': dataset.id
            }
        )
        request.user = user
        query_view = QueryViewCheck.as_view()
        response = query_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['valid'], False)

        query_string = 'truncate table georepo_geographicalentity'
        request = self.factory.post(
            reverse('query-view-check'), {
                'query_string': query_string,
                'dataset': dataset.id
            }
        )
        request.user = user
        query_view = QueryViewCheck.as_view()
        response = query_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['valid'], False)

    def test_query_check_with_quotes(self):
        query_string = (
            "select * from georepo_geographicalentity WHERE label=\"test\""
        )
        user = UserF.create()
        dataset = DatasetF.create()
        GeographicalEntityF.create(
            dataset=dataset
        )
        request = self.factory.post(
            reverse('query-view-check'), {
                'query_string': query_string,
                'dataset': dataset.id
            }
        )
        request.user = user
        query_view = QueryViewCheck.as_view()
        response = query_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['valid'], True)

    def test_query_check_with_go(self):
        query_string = (
            "select * from georepo_geographicalentity WHERE label='TW20_AGO'"
        )
        user = UserF.create()
        dataset = DatasetF.create()
        GeographicalEntityF.create(
            dataset=dataset
        )
        request = self.factory.post(
            reverse('query-view-check'), {
                'query_string': query_string,
                'dataset': dataset.id
            }
        )
        request.user = user
        query_view = QueryViewCheck.as_view()
        response = query_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['valid'], True)

    def test_column_table_list(self):
        user = UserF.create()
        request = self.factory.get(
            reverse('columns-tables-list'),
        )
        request.user = user
        query_view = SQLColumnsTablesList.as_view()
        response = query_view(request)
        self.assertEqual(response.status_code, 200)

    def test_preview_query(self):
        query_string = (
            'select * from georepo_geographicalentity WHERE label=\'test\''
        )
        GeographicalEntityF.create()
        user = UserF.create()
        dataset = DatasetF.create()
        request = self.factory.post(
            reverse('query-view-preview'), {
                'query_string': query_string,
                'dataset': dataset.id
            }
        )
        request.user = user
        query_view = QueryViewPreview.as_view()
        response = query_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['session'])
        self.assertTrue(
            EntitiesUserConfig.objects.filter(
                uuid=response.data['session']
            ).exists()
        )

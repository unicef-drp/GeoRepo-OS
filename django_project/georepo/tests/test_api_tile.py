import mock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from georepo.tests.model_factories import UserF
from georepo.api_views.tile import TileAPIView


class TestTileApiView(TestCase):

    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.superuser = UserF.create(is_superuser=True)

    @mock.patch('os.path.exists')
    def test_fetch_tile(self, mockExists):
        kwargs = {
            'resource': 'abcdef',
            'z': 0,
            'x': 0,
            'y': 0,
        }
        mockExists.return_value = False
        request = self.factory.get(
            reverse(
                'download-vector-tile',
                kwargs=kwargs
            )
        )
        view = TileAPIView.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        mockExists.return_value = True
        with mock.patch('builtins.open', mock.mock_open(read_data='test')):
            response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)

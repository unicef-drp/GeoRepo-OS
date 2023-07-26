from django.http import HttpRequest
from django.test import TestCase
from georepo.utils.url_helper import (
    get_ucode_from_url_path,
    get_page_size
)


class TestUtilsUrlHelper(TestCase):

    def test_extract_ucode(self):
        url_path_1 = '/ZAK/NC_0003_V1/2014-12-05/'
        url_path_2 = '/ZAK/NC_0003_V1/level/0/'
        ucode, data = get_ucode_from_url_path(url_path_1, -1)
        self.assertEqual(ucode, 'ZAK/NC_0003_V1')
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], '2014-12-05')
        ucode, data = get_ucode_from_url_path(url_path_2, -2)
        self.assertEqual(ucode, 'ZAK/NC_0003_V1')
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0], 'level')
        self.assertEqual(data[1], '0')

    def test_get_page_size(self):
        request = HttpRequest()
        # above max size
        request.GET = {
            'page_size': 100
        }
        page_size = get_page_size(request)
        self.assertEqual(page_size, 30)
        # not specified
        request.GET = {}
        page_size = get_page_size(request)
        self.assertEqual(page_size, 30)
        # accepted size
        request.GET = {
            'page_size': '10'
        }
        page_size = get_page_size(request)
        self.assertEqual(page_size, 10)

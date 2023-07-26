from django.test import TestCase
from georepo.utils.api_version import version_gt


class TestCompareAPIVersion(TestCase):

    def test_version_gt(self):
        value = 1
        version = 'v2'
        self.assertTrue(version_gt(version, value))

# coding=utf-8
"""
GeoSight is UNICEF's geospatial web-based business intelligence platform.

Contact : geosight-no-reply@unicef.org

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

"""
__author__ = 'zakki@kartoza.com'
__date__ = '14/08/23'
__copyright__ = ('Copyright 2023, Unicef')


import os
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from factory.django import FileField

from georepo.tests.model_factories import (
    DatasetF,
    LanguageF,
    ModuleF,
    UserF
)

from dashboard.api_views.upload_session import UploadSessionSummary
from dashboard.tests.model_factories import (
    LayerUploadSessionF,
    LayerFileF
)


class TestUploadSessionSummary(TestCase):

    def setUp(self) -> None:
        self.language = LanguageF.create(
            name='English',
            code='EN'
        )
        self.module = ModuleF.create(
            name='Admin Boundaries'
        )
        self.dataset = DatasetF.create(
            module=self.module
        )
        self.layer_upload_session = LayerUploadSessionF.create(
            dataset=self.dataset
        )
        self.superuser = UserF.create(is_superuser=True)
        self.layer_file = LayerFileF.create(
            layer_file=FileField(filename=f'{uuid4().hex}.geojson'),
            layer_type='GEOJSON',
            layer_upload_session=self.layer_upload_session,
            feature_count=1,
            name_fields=[
                {
                    "id": "1",
                    "field": "NAME_EN",
                    "label": "",
                    "default": True,
                    "duplicateError": False,
                    "selectedLanguage": self.language.id
                }
            ],
            id_fields=[
                {
                    "id": "1", "field": "PCODE",
                    "idType": {"id": 1, "name": "PCode"},
                    "default": True
                }
            ]
        )
        self.factory = APIRequestFactory()

    def test_upload_session_summary(self):
        request = self.factory.get(
            reverse(
                'upload-session-summary',
                kwargs={'pk': self.layer_upload_session.id}
            )
        )
        request.user = self.superuser
        view = UploadSessionSummary.as_view()
        response = view(request, self.layer_upload_session.id)
        expected_response = {
            'is_read_only': False,
            'summaries': [
                {
                    'id': self.layer_file.id,
                    'level': self.layer_file.level,
                    'file_name': os.path.basename(
                        self.layer_file.layer_file.name
                    ),
                    'field_mapping': [
                        'name_field (English) = NAME_EN (default)',
                        'id_field (PCode) = PCODE (default)',
                        'parent_id_field = ',
                        f"location_type = '{self.layer_file.entity_type}'",
                        'privacy_level_field = ',
                        'source_id_field = '
                    ],
                    'feature_count': 1,
                    'valid': True
                }
            ]
        }
        self.assertEquals(response.data, expected_response)

from django.utils import timezone

from georepo.models.export_request import (
    ExportRequest,
    GEOJSON_EXPORT_TYPE
)
from georepo.models.entity import EntityName
from georepo.utils.exporter_base import DatasetViewExporterBase
from georepo.tests.common import BaseDatasetViewTest


class TestExporter(BaseDatasetViewTest):

    def setUp(self):
        super().setUp()

    def test_filter_country(self):
        filters = {
            'country': ['Pakistan']
        }
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            filters=filters
        )
        exporter = DatasetViewExporterBase(request)
        exporter.init_exporter()
        qs = exporter.generate_queryset()
        self.assertEqual(qs.count(), 4)


    def test_filter_privacy_level(self):
        filters = {
            'privacy_level': [3]
        }
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            filters=filters
        )
        exporter = DatasetViewExporterBase(request)
        exporter.init_exporter()
        qs = exporter.generate_queryset()
        self.assertEqual(qs.count(), 1)

    def test_filter_level(self):
        filters = {
            'country': ['Pakistan'],
            'level': [1]
        }
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            filters=filters
        )
        exporter = DatasetViewExporterBase(request)
        exporter.init_exporter()
        qs = exporter.generate_queryset()
        self.assertEqual(qs.count(), 3)

    def test_filter_admin_level_name(self):
        filters = {
            'admin_level_name': ['Country']
        }
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            filters=filters
        )
        exporter = DatasetViewExporterBase(request)
        exporter.init_exporter()
        qs = exporter.generate_queryset()
        self.assertEqual(qs.count(), 1)

    def test_filter_type(self):
        filters = {
            'type': ['Region']
        }
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            filters=filters
        )
        exporter = DatasetViewExporterBase(request)
        exporter.init_exporter()
        qs = exporter.generate_queryset()
        self.assertEqual(qs.count(), 3)

    def test_filter_revision(self):
        filters = {
            'revision': [2]
        }
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            filters=filters
        )
        exporter = DatasetViewExporterBase(request)
        exporter.init_exporter()
        qs = exporter.generate_queryset()
        self.assertEqual(qs.count(), 4)

    def test_filter_source(self):
        filters = {
            'source': ['ABCD']
        }
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            filters=filters
        )
        exporter = DatasetViewExporterBase(request)
        exporter.init_exporter()
        qs = exporter.generate_queryset()
        self.assertEqual(qs.count(), 1)

    def test_filter_valid_from(self):
        filters = {
            'valid_from': '2023-01-10T07:16:13Z'
        }
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            filters=filters
        )
        exporter = DatasetViewExporterBase(request)
        exporter.init_exporter()
        qs = exporter.generate_queryset()
        self.assertEqual(qs.count(), 4)

    def test_filter_search_text(self):
        self.assertTrue(EntityName.objects.filter(
            geographical_entity=self.pak0_2,
            name__icontains='pktn'
        ).exists())
        filters = {
            'search_text': 'pktn'
        }
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            filters=filters
        )
        exporter = DatasetViewExporterBase(request)
        exporter.init_exporter()
        qs = exporter.generate_queryset()
        self.assertEqual(qs.count(), 1)

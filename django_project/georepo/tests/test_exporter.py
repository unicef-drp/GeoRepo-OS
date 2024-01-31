from django.utils import timezone
import datetime
from django.core.files.uploadedfile import SimpleUploadedFile
from core.settings.utils import absolute_path
from georepo.models.export_request import (
    ExportRequest,
    GEOJSON_EXPORT_TYPE,
    SHAPEFILE_EXPORT_TYPE,
    KML_EXPORT_TYPE,
    TOPOJSON_EXPORT_TYPE,
    ExportRequestStatusText
)
from georepo.models.entity import EntityName, EntitySimplified
from georepo.utils.exporter_base import DatasetViewExporterBase
from georepo.utils.geojson import GeojsonViewExporter
from georepo.utils.shapefile import ShapefileViewExporter
from georepo.utils.kml import KmlViewExporter
from georepo.utils.topojson import TopojsonViewExporter
from georepo.tests.common import BaseDatasetViewTest
from georepo.tasks.dataset_view import expire_export_request


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

    def test_geojson_exporter(self):
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser
        )
        exporter = GeojsonViewExporter(request)
        exporter.init_exporter()
        exporter.run()
        request.refresh_from_db()
        self.assertTrue(request.download_link_expired_on)
        self.assertTrue(request.output_file)
        self.assertTrue(request.download_link)

    def test_shapefile_exporter(self):
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=SHAPEFILE_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser
        )
        exporter = ShapefileViewExporter(request)
        exporter.init_exporter()
        exporter.run()
        request.refresh_from_db()
        self.assertTrue(request.download_link_expired_on)
        self.assertTrue(request.output_file)
        self.assertTrue(request.download_link)

    def test_kml_exporter(self):
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=KML_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser
        )
        exporter = KmlViewExporter(request)
        exporter.init_exporter()
        exporter.run()
        request.refresh_from_db()
        self.assertTrue(request.download_link_expired_on)
        self.assertTrue(request.output_file)
        self.assertTrue(request.download_link)

    def test_topojson_exporter(self):
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=TOPOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser
        )
        exporter = TopojsonViewExporter(request)
        exporter.init_exporter()
        exporter.run()
        request.refresh_from_db()
        self.assertTrue(request.download_link_expired_on)
        self.assertTrue(request.output_file)
        self.assertTrue(request.download_link)

    def test_geojson_exporter_with_simplified_entities(self):
        # insert geometry to entity simplified
        EntitySimplified.objects.create(
            geographical_entity=self.pak0_2,
            simplify_tolerance=1,
            simplified_geometry=self.pak0_2.geometry
        )
        filters = {
            'country': ['Pakistan'],
            'level': [0]
        }
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            filters=filters,
            is_simplified_entities=True,
            simplification_zoom_level=0
        )
        exporter = GeojsonViewExporter(request)
        exporter.init_exporter()
        self.assertEqual(len(exporter.levels), 1)
        exporter.run()
        request.refresh_from_db()
        self.assertTrue(request.download_link_expired_on)
        self.assertTrue(request.output_file)
        self.assertTrue(request.download_link)

    def test_expire_request(self):
        test_file_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0_test_points.geojson')
        with open(test_file_path, 'rb') as data:
            file = SimpleUploadedFile(
                content=data.read(),
                name=data.name
            )
        request = ExportRequest.objects.create(
            dataset_view=self.dataset_view,
            format=GEOJSON_EXPORT_TYPE,
            submitted_on=timezone.now(),
            submitted_by=self.superuser,
            status_text=str(ExportRequestStatusText.READY),
            download_link='abc',
            download_link_expired_on=datetime.datetime(2000, 8, 14, 8, 8, 8),
            output_file=file
        )
        expire_export_request()
        request.refresh_from_db()
        self.assertFalse(request.output_file)
        self.assertFalse(request.download_link)
        self.assertEqual(request.status_text,
                         str(ExportRequestStatusText.EXPIRED))

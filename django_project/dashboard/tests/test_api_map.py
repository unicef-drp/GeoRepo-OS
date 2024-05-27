from django.urls import reverse
from georepo.models.dataset_view import (
    DatasetView
)
from georepo.utils.dataset_view import (
    generate_default_view_dataset_all_versions,
    init_view_privacy_level,
    calculate_entity_count_in_view,
    generate_view_bbox
)
from georepo.tests.common import (
    BaseDatasetViewTest
)
from dashboard.api_views.map import (
    DatasetBbox,
    ViewBbox
)


class TestMapAPI(BaseDatasetViewTest):

    def setUp(self):
        super().setUp()
        generate_default_view_dataset_all_versions(self.dataset)
        self.dataset_view_2 = DatasetView.objects.filter(
            dataset=self.dataset,
            default_type=DatasetView.DefaultViewType.ALL_VERSIONS,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(self.dataset_view_2)
        calculate_entity_count_in_view(self.dataset_view_2)
        generate_view_bbox(self.dataset_view_2)


    def test_get_dataset_bbox(self):
        kwargs = {
            'id': str(self.dataset.uuid)
        }
        request = self.factory.get(
            reverse('dataset-bbox',
                    kwargs=kwargs)
        )
        request.user = self.superuser
        view = DatasetBbox.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def test_get_viewu_bbox(self):
        kwargs = {
            'id': str(self.dataset_view_2.uuid)
        }
        request = self.factory.get(
            reverse('dataset-view-bbox',
                    kwargs=kwargs)
        )
        request.user = self.superuser
        view = ViewBbox.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

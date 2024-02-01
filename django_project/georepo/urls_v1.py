import os
from django.urls import path, re_path
from django.conf import settings
from georepo.api_views.module import (
    ModuleList
)
from georepo.api_views.dataset import (
    DatasetList,
    DatasetDetail,
    DatasetEntityListHierarchical,
    DatasetExportDownload,
    DatasetExportDownloadByLevel,
    DatasetExportDownloadByCountry,
    DatasetExportDownloadByCountryAndLevel
)
from georepo.api_views.dataset_view import (
    DatasetViewList,
    DatasetViewListForUser,
    DatasetViewDetail,
    DatasetViewExportDownload,
    DatasetViewExportDownloadByLevel,
    DatasetViewExportDownloadByCountry,
    DatasetViewExportDownloadByCountryAndLevel,
    DatasetViewCentroid
)
from georepo.api_views.entity_view import (
    FindViewEntityById,
    ViewEntityListByAdminLevel,
    ViewEntityListByAdminLevelAndUCode,
    ViewEntityListByEntityType,
    ViewEntityListByEntityTypeAndUcode,
    ViewFindEntityVersionsByConceptUCode,
    ViewFindEntityVersionsByUCode,
    ViewFindEntityFuzzySearch,
    ViewFindEntityGeometryFuzzySearch,
    ViewEntityBoundingBox,
    ViewEntityContainmentCheck,
    ViewEntityTraverseHierarchyByUCode,
    ViewEntityTraverseChildrenHierarchyByUCode,
    ViewEntityListByAdminLevel0,
    ViewEntityListByAdminLevelAndConceptUCode,
    ViewEntityBatchSearchId,
    ViewEntityBatchGeocoding,
    ViewEntityBatchSearchIdStatus,
    ViewEntityBatchSearchIdResult,
    ViewEntityBatchGeocodingResult,
    ViewEntityBatchGeocodingStatus
)
from georepo.api_views.entity import (
    EntityBoundingBox,
    EntityTypeList,
    EntityIdList,
    EntityContainmentCheck,
    EntityFuzzySearch,
    EntityGeometryFuzzySearch,
    EntityList,
    EntityListByUCode,
    EntityListByAdminLevel,
    EntityListByAdminLevelAndUCode,
    FindEntityById,
    FindEntityVersionsByConceptUCode,
    FindEntityVersionsByUCode
)
module_urls = [
    path(
        'search/module/list/',
        ModuleList.as_view(),
        name='module-list'
    )
]

dataset_urls = [
    re_path(
        r'search/module/(?P<uuid>[\da-f-]+)/dataset/list/?$',
        DatasetList.as_view(),
        name='dataset-list'),
    re_path(
        r'search/dataset/(?P<uuid>[\da-f-]+)/?$',
        DatasetDetail.as_view(),
        name='dataset-detail'),
]

entity_urls = [
    re_path(
        r'search/dataset/(?P<uuid>[\da-f-]+)/entity/hierarchy'
        r'/(?P<concept_uuid>[\da-f-]+)/?$',
        DatasetEntityListHierarchical.as_view(),
        name='dataset-entity-hierarchy'
    ),
    re_path(
        r'search/dataset/(?P<uuid>[\da-f-]+)/entity/type/'
        r'(?P<entity_type>[^/]+)/?$',
        EntityList.as_view(),
        name='search-entity-by-type'),
    path(
        'search/dataset/<uuid:uuid>/entity/type/'
        '<entity_type>/<path:ucode>/',
        EntityListByUCode.as_view(),
        name='search-entity-by-type-and-ucode'),
    re_path(
        r'search/dataset/(?P<uuid>[\da-f-]+)/entity/level/'
        r'(?P<admin_level>[\d]+)/?$',
        EntityListByAdminLevel.as_view(),
        name='search-entity-by-level'),
    path(
        'search/dataset/<uuid:uuid>/entity/level/'
        '<int:admin_level>/<path:ucode>/',
        EntityListByAdminLevelAndUCode.as_view(),
        name='search-entity-by-level-and-ucode'),
    re_path(
        r'search/dataset/(?P<uuid>[\da-f-]+)/entity/'
        r'version/(?P<concept_ucode>#[^/]+)/?$',
        FindEntityVersionsByConceptUCode.as_view(),
        name='search-entity-versions-by-concept-ucode'),
    path(
        'search/dataset/<uuid:uuid>/entity/'
        'version/<path:ucode>/',
        FindEntityVersionsByUCode.as_view(),
        name='search-entity-versions-by-ucode'),
    path(
        'search/dataset/<uuid:uuid>/entity/identifier/'
        '<id_type>/<path:id>/',
        FindEntityById.as_view(),
        name='search-entity-by-id'),
    re_path(
        r'search/dataset/(?P<uuid>[\da-f-]+)/entity/geometry/?$',
        EntityGeometryFuzzySearch.as_view(),
        name='entity-fuzzy-search-by-geometry'
    ),
    path(
        'search/dataset/<uuid:uuid>/entity/'
        '<path:search_text>/',
        EntityFuzzySearch.as_view(),
        name='entity-fuzzy-search-by-name'
    ),
]

operation_entity_urls = [
    path(
        'operation/dataset/<uuid:uuid>/bbox/<id_type>/'
        '<path:id>/',
        EntityBoundingBox.as_view(),
        name='entity-bounding-box'
    ),
    re_path(
        r'operation/dataset/(?P<uuid>[\da-f-]+)/containment-check/'
        r'(?P<spatial_query>[^/]+)/(?P<distance>[\d]+)/'
        r'(?P<id_type>[^/]+)/?$',
        EntityContainmentCheck.as_view(),
        name='entity-containment-check'
    ),
]

view_urls = [
    re_path(
        r'search/dataset/(?P<uuid>[\da-f-]+)/view/list/',
        DatasetViewList.as_view(),
        name='view-list-by-dataset'),
    re_path(
        r'search/view/list/',
        DatasetViewListForUser.as_view(),
        name='view-list'),
    re_path(
        r'search/view/(?P<uuid>[\da-f-]+)/centroid/',
        DatasetViewCentroid.as_view(),
        name='view-centroid'),
    re_path(
        r'search/view/(?P<uuid>[\da-f-]+)/',
        DatasetViewDetail.as_view(),
        name='view-detail'),
]

view_entity_urls = [
    path(
        'search/view/<uuid:uuid>/entity/batch/identifier/<str:input_type>/',
        ViewEntityBatchSearchId.as_view(),
        name='batch-search-view-by-id'
    ),
    path(
        'search/view/<uuid:uuid>/entity/batch/identifier/'
        'status/<uuid:request_id>/',
        ViewEntityBatchSearchIdStatus.as_view(),
        name='batch-status-search-view-by-id'
    ),
    path(
        'search/view/<uuid:uuid>/entity/batch/identifier/'
        'result/<uuid:request_id>/',
        ViewEntityBatchSearchIdResult.as_view(),
        name='batch-result-search-view-by-id'
    ),
    re_path(
        r'search/view/(?P<uuid>[\da-f-]+)/entity/list/?$',
        ViewEntityListByAdminLevel0.as_view(),
        name='search-view-entity-list'),
    path(
        'search/view/<uuid:uuid>/entity/identifier/<str:id_type>/<str:id>/',
        FindViewEntityById.as_view(),
        name='search-view-entity-by-id'),
    re_path(
        r'search/view/(?P<uuid>[\da-f-]+)/entity/level/'
        r'(?P<admin_level>[\d]+)/?$',
        ViewEntityListByAdminLevel.as_view(),
        name='search-view-entity-by-level'),
    re_path(
        r'search/view/(?P<uuid>[\da-f-]+)/entity/level/'
        r'(?P<admin_level>[\d]+)/(?P<concept_ucode>#[^/]+)/?$',
        ViewEntityListByAdminLevelAndConceptUCode.as_view(),
        name='search-view-entity-by-level-and-concept-ucode'),
    re_path(
        r'search/view/(?P<uuid>[\da-f-]+)/entity/level/'
        r'(?P<admin_level>[\d]+)/(?P<ucode>[^/]+)/?$',
        ViewEntityListByAdminLevelAndUCode.as_view(),
        name='search-view-entity-by-level-and-ucode'),
    re_path(
        r'search/view/(?P<uuid>[\da-f-]+)/entity/type/'
        r'(?P<entity_type>[^/]+)/?$',
        ViewEntityListByEntityType.as_view(),
        name='search-view-entity-by-type'),
    path(
        'search/view/<uuid:uuid>/entity/type/'
        '<entity_type>/<path:ucode>/',
        ViewEntityListByEntityTypeAndUcode.as_view(),
        name='search-view-entity-by-type-and-ucode'),
    re_path(
        r'search/view/(?P<uuid>[\da-f-]+)/entity/'
        r'version/(?P<concept_ucode>#[^/]+)/?$',
        ViewFindEntityVersionsByConceptUCode.as_view(),
        name='search-view-entity-versions-by-concept-ucode'),
    path(
        'search/view/<uuid:uuid>/entity/'
        'version/<path:ucode>/',
        ViewFindEntityVersionsByUCode.as_view(),
        name='search-view-entity-versions-by-ucode'),
    re_path(
        r'search/view/(?P<uuid>[\da-f-]+)/entity/geometry/?$',
        ViewFindEntityGeometryFuzzySearch.as_view(),
        name='view-entity-fuzzy-search-by-geometry'
    ),
    path(
        'search/view/<uuid:uuid>/entity/'
        '<path:ucode>/parent/',
        ViewEntityTraverseHierarchyByUCode.as_view(),
        name='search-view-entity-parent-by-ucode'),
    path(
        'search/view/<uuid:uuid>/entity/'
        '<path:ucode>/children/',
        ViewEntityTraverseChildrenHierarchyByUCode.as_view(),
        name='search-view-entity-children-by-ucode'),
    path(
        'search/view/<uuid:uuid>/entity/'
        '<path:search_text>/',
        ViewFindEntityFuzzySearch.as_view(),
        name='view-entity-fuzzy-search-by-name'
    ),
]

operation_view_entity_urls = [
    path(
        'operation/view/<uuid:uuid>/bbox/<id_type>/'
        '<path:id>/',
        ViewEntityBoundingBox.as_view(),
        name='view-entity-bounding-box'
    ),
    re_path(
        r'operation/view/(?P<uuid>[\da-f-]+)/containment-check/'
        r'(?P<spatial_query>[^/]+)/(?P<distance>[\d]+)/'
        r'(?P<id_type>[^/]+)/?$',
        ViewEntityContainmentCheck.as_view(),
        name='view-entity-containment-check'
    ),
    path(
        'operation/view/<uuid:uuid>/batch-containment-check/'
        'status/<uuid:request_id>/',
        ViewEntityBatchGeocodingStatus.as_view(),
        name='check-status-batch-geocoding'
    ),
    path(
        'operation/view/<uuid:uuid>/batch-containment-check/'
        'result/<uuid:request_id>/',
        ViewEntityBatchGeocodingResult.as_view(),
        name='get-result-batch-geocoding'
    ),
    re_path(
        r'operation/view/(?P<uuid>[\da-f-]+)/batch-containment-check/'
        r'(?P<spatial_query>[^/]+)/(?P<distance>[\d]+)/'
        r'(?P<admin_level>[\d]+)/(?P<id_type>[^/]+)/?$',
        ViewEntityBatchGeocoding.as_view(),
        name='batch-geocoding'
    ),
]

download_urls = [
    re_path(
        r'download/view/(?P<uuid>[\da-f-]+)/?$',
        DatasetViewExportDownload.as_view(),
        name='dataset-view-download'),
    re_path(
        r'download/view/(?P<uuid>[\da-f-]+)/level/'
        r'(?P<admin_level>[\d]+)/?$',
        DatasetViewExportDownloadByLevel.as_view(),
        name='dataset-view-download-by-level'),
    path(
        'download/view/<uuid:uuid>/identifier/'
        '<id_type>/<path:id>/'
        'level/<int:admin_level>/',
        DatasetViewExportDownloadByCountryAndLevel.as_view(),
        name='dataset-view-download-by-country-and-level'),
    path(
        'download/view/<uuid:uuid>/identifier/'
        '<id_type>/<path:id>/',
        DatasetViewExportDownloadByCountry.as_view(),
        name='dataset-view-download-by-country'),
]

download_dataset_urls = [
    re_path(
        r'download/dataset/(?P<uuid>[\da-f-]+)/?$',
        DatasetExportDownload.as_view(),
        name='dataset-download'),
    re_path(
        r'download/dataset/(?P<uuid>[\da-f-]+)/level/'
        r'(?P<admin_level>[\d]+)/?$',
        DatasetExportDownloadByLevel.as_view(),
        name='dataset-download-by-level'),
    path(
        'download/dataset/<uuid:uuid>/identifier/'
        '<id_type>/<path:id>/'
        'level/<int:admin_level>/',
        DatasetExportDownloadByCountryAndLevel.as_view(),
        name='dataset-download-by-country-and-level'),
    path(
        'download/dataset/<uuid:uuid>/identifier/'
        '<id_type>/<path:id>/',
        DatasetExportDownloadByCountry.as_view(),
        name='dataset-download-by-country'),
]

controlled_list_urls = [
    re_path(
        r'controlled-list/entity-type/?$',
        EntityTypeList.as_view(),
        name='entity-type-list'
    ),
    re_path(
        r'controlled-list/id-type/?$',
        EntityIdList.as_view(),
        name='id-type-list'
    )
]

urlpatterns = []
urlpatterns += module_urls
urlpatterns += dataset_urls
if (
    settings.DEBUG or
    'dev' in os.environ['DJANGO_SETTINGS_MODULE'] or
    'test' in os.environ['DJANGO_SETTINGS_MODULE']
):
    urlpatterns += entity_urls
    urlpatterns += operation_entity_urls
    urlpatterns += download_dataset_urls
urlpatterns += view_entity_urls
urlpatterns += operation_view_entity_urls
urlpatterns += download_urls
urlpatterns += controlled_list_urls
urlpatterns += view_urls

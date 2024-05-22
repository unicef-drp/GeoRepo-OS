import uuid
import json
import mock
import random
from dateutil.parser import isoparse
from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import GEOSGeometry
from guardian.shortcuts import assign_perm

from rest_framework.test import APIRequestFactory
from rest_framework import versioning

from georepo.utils import absolute_path
from georepo.models import IdType, DatasetView
from georepo.tests.model_factories import (
    GeographicalEntityF, EntityTypeF, DatasetF, EntityIdF,
    EntityNameF, LanguageF, UserF, GroupF
)
from georepo.api_views.entity_view import (
    FindViewEntityById,
    ViewEntityListByAdminLevel,
    ViewEntityListByAdminLevelAndUCode,
    ViewEntityListByEntityType,
    ViewEntityListByEntityTypeAndUcode,
    ViewFindEntityVersionsByConceptUCode,
    ViewFindEntityVersionsByUCode,
    ViewEntityBoundingBox,
    ViewEntityContainmentCheck,
    ViewFindEntityFuzzySearch,
    ViewFindEntityGeometryFuzzySearch,
    ViewEntityTraverseHierarchyByUCode,
    ViewEntityTraverseChildrenHierarchyByUCode,
    ViewEntityListByAdminLevel0,
    FindEntityByUCode,
    FindEntityByCUCode
)
from georepo.tests.common import EntityResponseChecker, BaseDatasetViewTest
from georepo.utils.dataset_view import (
    generate_default_view_dataset_latest,
    generate_default_view_dataset_all_versions,
    generate_default_view_adm0_latest,
    generate_default_view_adm0_all_versions,
    init_view_privacy_level,
    create_sql_view,
    calculate_entity_count_in_view
)
from georepo.utils.permission import (
    grant_datasetview_external_viewer,
    revoke_datasetview_external_viewer,
    grant_dataset_viewer
)


class EntityViewTestSuite(EntityResponseChecker):

    def call_setup(self) -> None:
        """
        revision=1 -> is_latest=False
        level 0 -> PAK
        level 1 -> PAK_001, PAK_002

        revision=2 -> is_latest=True
        level 0 -> PAK
        level 1 -> PAK_001, PAK_002 (new concept), PAK_003
        """
        self.factory = APIRequestFactory()
        self.enLang = LanguageF.create(
            code='EN',
            name='English'
        )
        self.esLang = LanguageF.create(
            code='ES',
            name='Spanist'
        )
        self.superuser = UserF.create(is_superuser=True)
        self.pCode = IdType.objects.get(name='PCode')
        self.entity_type0 = EntityTypeF.create(label='Country')
        self.entity_type1 = EntityTypeF.create(label='Region')
        self.dataset = DatasetF.create()

        # bob should have no access to current dataset
        self.bob_user = UserF.create(username='bob')
        # moz should have access to current dataset with level 3
        self.moz_user = UserF.create(username='moz')
        assign_perm('view_dataset_level_3', self.moz_user, self.dataset)
        # zac should have external permission a view (no dataset permission)
        self.zac_user = UserF.create(username='zac')

        # create group viewer with level 1, add meo to the group
        self.dan_user = UserF.create(username='dan')
        self.viewer_1 = GroupF.create()
        assign_perm('view_dataset_level_1', self.viewer_1, self.dataset)
        self.dan_user.groups.add(self.viewer_1)

        geojson_0_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_0_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            geom = GEOSGeometry(geom_str)
            self.pak0_1 = GeographicalEntityF.create(
                dataset=self.dataset,
                level=0,
                admin_level_name='Country',
                type=self.entity_type0,
                is_validated=True,
                is_approved=True,
                is_latest=False,
                geometry=geom,
                internal_code='PAK',
                revision_number=1,
                label='Pakistan',
                unique_code='PAK',
                unique_code_version=1,
                start_date=isoparse('2023-01-01T06:16:13Z'),
                end_date=isoparse('2023-01-10T06:16:13Z'),
                concept_ucode='#PAK_1',
                centroid=geom.point_on_surface.wkt,
                bbox='[' + ','.join(map(str, geom.extent)) + ']'
            )
            EntityIdF.create(
                code=self.pCode,
                geographical_entity=self.pak0_1,
                default=True,
                value=self.pak0_1.internal_code
            )
            EntityNameF.create(
                geographical_entity=self.pak0_1,
                name=self.pak0_1.label,
                language=self.enLang,
                idx=0
            )
            self.pak0_2 = GeographicalEntityF.create(
                dataset=self.dataset,
                level=0,
                admin_level_name='Country',
                type=self.entity_type0,
                is_validated=True,
                is_approved=True,
                is_latest=True,
                geometry=geom,
                internal_code='PAK',
                revision_number=2,
                label='Pakistan',
                unique_code='PAK',
                unique_code_version=2,
                start_date=isoparse('2023-01-10T06:16:13Z'),
                uuid=self.pak0_1.uuid,
                concept_ucode=self.pak0_1.concept_ucode,
                centroid=geom.point_on_surface.wkt,
                bbox='[' + ','.join(map(str, geom.extent)) + ']'
            )
            EntityIdF.create(
                code=self.pCode,
                geographical_entity=self.pak0_2,
                default=True,
                value=self.pak0_2.internal_code
            )
            EntityNameF.create(
                geographical_entity=self.pak0_2,
                name=self.pak0_2.label,
                language=self.enLang,
                idx=0
            )
        geojson_1_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_1.geojson')
        with open(geojson_1_path) as geojson:
            data = json.load(geojson)
            geom_str = json.dumps(data['features'][0]['geometry'])
            self.entities_1 = []
            self.entities_2 = []
            entity_1_uuid = None
            entity_1_cucode = None
            v1_idx = [0, 1]
            random.shuffle(v1_idx)
            temp_entities = {}
            for i in v1_idx:
                geom = GEOSGeometry(geom_str)
                entity = GeographicalEntityF.create(
                    parent=self.pak0_1,
                    ancestor=self.pak0_1,
                    level=1,
                    admin_level_name='Region',
                    dataset=self.dataset,
                    type=self.entity_type1,
                    is_validated=True,
                    is_approved=True,
                    is_latest=False,
                    geometry=geom,
                    internal_code=f'PAK00{i+1}',
                    revision_number=1,
                    label='Khyber Pakhtunkhwa',
                    unique_code=f'PAK_000{i+1}',
                    unique_code_version=1,
                    start_date=isoparse('2023-01-01T06:16:13Z'),
                    end_date=isoparse('2023-01-10T06:16:13Z'),
                    concept_ucode=f'#PAK_{i+2}',
                    centroid=geom.point_on_surface.wkt,
                    bbox='[' + ','.join(map(str, geom.extent)) + ']'
                )
                if i == 0:
                    entity_1_uuid = entity.uuid
                    entity_1_cucode = entity.concept_ucode
                EntityIdF.create(
                    code=self.pCode,
                    geographical_entity=entity,
                    default=True,
                    value=entity.internal_code
                )
                EntityNameF.create(
                    geographical_entity=entity,
                    name=entity.label,
                    language=self.enLang,
                    idx=0
                )
                temp_entities[i] = entity
            v1_idx.sort()
            self.entities_1 = [temp_entities[i] for i in v1_idx]

            privacy_levels = [4, 3, 1]
            v2_idx = [0, 1, 2]
            random.shuffle(v2_idx)
            temp_entities2 = {}
            for i in v2_idx:
                geom = GEOSGeometry(geom_str)
                entity = GeographicalEntityF.create(
                    parent=self.pak0_2,
                    ancestor=self.pak0_2,
                    level=1,
                    admin_level_name='Region',
                    dataset=self.dataset,
                    type=self.entity_type1,
                    is_validated=True,
                    is_approved=True,
                    is_latest=True,
                    geometry=geom,
                    internal_code=f'PAK00{i+1}',
                    revision_number=2,
                    label='Khyber Pakhtunkhwa',
                    unique_code=f'PAK_000{i+1}',
                    unique_code_version=2,
                    start_date=isoparse('2023-01-10T06:16:13Z'),
                    privacy_level=privacy_levels[i],
                    concept_ucode=f'#PAK_{i+4}',
                    centroid=geom.point_on_surface.wkt,
                    bbox='[' + ','.join(map(str, geom.extent)) + ']'
                )
                if i == 0:
                    entity.uuid = entity_1_uuid
                    entity.concept_ucode = entity_1_cucode
                    entity.save()
                EntityIdF.create(
                    code=self.pCode,
                    geographical_entity=entity,
                    default=True,
                    value=entity.internal_code
                )
                EntityNameF.create(
                    geographical_entity=entity,
                    name=entity.label,
                    language=self.enLang,
                    idx=0
                )
                temp_entities2[i] = entity
            v2_idx.sort()
            self.entities_2 = [temp_entities2[i] for i in v2_idx]
        self.generate_default_view()

    def generate_default_view(self):
        raise NotImplementedError('generate_default_view')

    def assert_find_view_entity_by_id_by_ucode(self, response):
        raise NotImplementedError('assert_find_view_entity_by_id_by_ucode')

    def assert_find_view_entity_by_id_by_cucode(self, response):
        raise NotImplementedError('assert_find_view_entity_by_id_by_cucode')

    def assert_find_view_entity_by_id_by_pcode(self, response):
        raise NotImplementedError('assert_find_view_entity_by_id_by_pcode')

    def assert_find_view_entity_by_pcode_and_timestamp(self, response):
        raise NotImplementedError(
            'assert_find_view_entity_by_pcode_and_timestamp'
        )

    def assert_find_view_entity_by_level_0(self, response):
        raise NotImplementedError('assert_find_view_entity_by_level_0')

    def assert_find_view_entity_by_level_1(self, response):
        raise NotImplementedError('assert_find_view_entity_by_level_1')

    def assert_find_view_entity_by_level_1_ucode(self, response):
        raise NotImplementedError('assert_find_view_entity_by_level_1_ucode')

    def assert_find_view_entity_by_country(self, response):
        raise NotImplementedError('assert_find_view_entity_by_country')

    def assert_find_view_entity_by_region(self, response):
        raise NotImplementedError('assert_find_view_entity_by_region')

    def assert_find_view_entity_by_region_ucode(self, response):
        raise NotImplementedError('assert_find_view_entity_by_region_ucode')

    def assert_find_view_entity_versions_by_concept(self, response):
        raise NotImplementedError(
            'assert_find_view_entity_versions_by_concept'
        )

    def assert_find_view_entity_versions_by_ucode_pak0_2(self, response):
        raise NotImplementedError(
            'assert_find_view_entity_versions_by_ucode_pak0_2'
        )

    def assert_find_view_entity_versions_by_ucode_pak0_1(self, response):
        raise NotImplementedError(
            'assert_find_view_entity_versions_by_ucode_pak0_1'
        )

    def assert_find_view_entity_versions_by_ucode_entities1_1(self, response):
        raise NotImplementedError(
            'assert_find_view_entity_versions_by_ucode_entities1_1'
        )

    def assert_find_view_entity_versions_by_ucode_ts_v1(self, response):
        raise NotImplementedError(
            'assert_find_view_entity_versions_by_ucode_ts_v1'
        )

    def assert_find_view_entity_versions_by_ucode_ts_v2(self, response):
        raise NotImplementedError(
            'assert_find_view_entity_versions_by_ucode_ts_v2'
        )

    def assert_view_entity_bbox_pcode_pak(self, response):
        raise NotImplementedError(
            'assert_view_entity_bbox_pcode_pak'
        )

    def assert_view_entity_bbox_uuid_pak0_1(self, response):
        raise NotImplementedError(
            'assert_view_entity_bbox_uuid_pak0_1'
        )

    def assert_view_entity_containment_check_intersects(self, response):
        raise NotImplementedError(
            'assert_view_entity_containment_check_intersects'
        )

    def assert_view_entity_containment_check_intersects_cucode(self,
                                                               response):
        raise NotImplementedError(
            'assert_view_entity_containment_check_intersects_cucode'
        )

    def assert_view_entity_containment_check_intersects_not_found(self,
                                                                  response):
        raise NotImplementedError(
            'assert_view_entity_containment_check_intersects_not_found'
        )

    def assert_view_entity_containment_check_within_found(self, response):
        raise NotImplementedError(
            'assert_view_entity_containment_check_within_found'
        )

    def assert_view_entity_containment_check_dwithin_found(self, response):
        raise NotImplementedError(
            'assert_view_entity_containment_check_dwithin_found'
        )

    def assert_view_entity_containment_check_within_centroid_found(self,
                                                                   response):
        raise NotImplementedError(
            'assert_view_entity_containment_check_within_centroid_found'
        )

    def assert_view_entity_containment_check_hierarchy(self, response):
        raise NotImplementedError(
            'assert_view_entity_containment_check_hierarchy'
        )

    def assert_view_entity_fuzzy_search_found1(self, response):
        raise NotImplementedError(
            'assert_view_entity_fuzzy_search_found1'
        )

    def assert_view_entity_fuzzy_search_found2(self, response):
        raise NotImplementedError(
            'assert_view_entity_fuzzy_search_found2'
        )

    def assert_view_entity_fuzzy_geom_search_found1(self, response):
        raise NotImplementedError(
            'assert_view_entity_fuzzy_geom_search_found1'
        )

    def assert_view_entity_fuzzy_geom_search_level2(self, response):
        raise NotImplementedError(
            'assert_view_entity_fuzzy_geom_search_level2'
        )

    def assert_find_view_entity_parent_by_ucode(self, response):
        raise NotImplementedError(
            'assert_find_view_entity_parent_by_ucode'
        )

    def assert_find_view_entity_children_by_ucode(self, response):
        raise NotImplementedError(
            'assert_find_view_entity_children_by_ucode'
        )

    def assert_find_view_entity_by_level_paginated(self, responses):
        raise NotImplementedError(
            'assert_find_view_entity_by_level_paginated'
        )

    def _run_test_permission(self, request, view, **kwargs):
        # test 401
        request.user = None
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 401)
        # test 403 with user bob
        request.user = self.bob_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 403)
        # test with user moz level 3
        request.user = self.moz_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        if 'results' in response.data:
            for item in response.data['results']:
                self.check_user_can_view_entity(item, self.moz_user)
        # test with user dan and group viewer level 1
        request.user = self.dan_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        if 'results' in response.data:
            for item in response.data['results']:
                self.check_user_can_view_entity(item, self.dan_user)
        # test zac user without external permission, should be 403
        request.user = self.zac_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 403)
        # test zac user with external permission in a view
        grant_datasetview_external_viewer(self.dataset_view, self.zac_user, 1)
        request.user = self.zac_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        if 'results' in response.data:
            for item in response.data['results']:
                self.check_user_can_view_entity(item, self.dan_user)
        revoke_datasetview_external_viewer(self.dataset_view, self.zac_user)
        # test disabled module
        self.dataset.module.is_active = False
        self.dataset.module.save()
        request.user = self.zac_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        self.dataset.module.is_active = True
        self.dataset.module.save()

    def run_test_find_view_entity_by_id(self):
        # search by ucode
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': 'ucode',
            'id': 'PAK_0001_V2'
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-id', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = FindViewEntityById.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_id_by_ucode(response)
        # search by concept ucode
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': 'concept_ucode',
            'id': '#PAK_1'
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-id', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = FindViewEntityById.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_id_by_cucode(response)
        # search by PCode
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': self.pCode.name,
            'id': 'PAK001'
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-id', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = FindViewEntityById.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_id_by_pcode(response)
        # search by invalid uuid
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': 'uuid',
            'id': str(uuid.uuid4())
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-id', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = FindViewEntityById.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        # search by pcode and timestamp
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': self.pCode.name,
            'id': 'PAK001'
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-by-id',
                kwargs=kwargs
            ) + '/?timestamp=2023-01-10T06:16:13Z'
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = FindViewEntityById.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_pcode_and_timestamp(response)
        # test permission
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': 'ucode',
            'id': 'PAK_0001_V2'
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-id', kwargs=kwargs)
        )
        self._run_test_permission(request, view, **kwargs)

    def run_test_find_view_entity_by_level_not_found(self):
        # search level 0
        kwargs = {
            'uuid': str(self.dataset.uuid),
            'admin_level': 0
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-level', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByAdminLevel.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)

    def run_test_find_view_entity_by_level(self):
        # search level 0
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'admin_level': 0
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-level', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByAdminLevel.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_level_0(response)
        # search level 1
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'admin_level': 1
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-level', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByAdminLevel.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_level_1(response)
        # search level 1 + ucode
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'admin_level': 1,
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-level-and-ucode',
                    kwargs=kwargs) + '/?cached=False&geom=centroid'
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByAdminLevelAndUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_level_1_ucode(response)
        # search list entities should return level 0 only
        kwargs = {
            'uuid': str(self.dataset_view.uuid)
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-list', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByAdminLevel0.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_level_0(response)
        # test permission
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'admin_level': 1
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-level', kwargs=kwargs)
        )
        self._run_test_permission(request, view, **kwargs)

    def run_test_find_view_entity_by_type(self):
        # search country
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'entity_type': self.entity_type0.label
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-type', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByEntityType.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_country(response)
        # search type region
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'entity_type': self.entity_type1.label
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-type', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByEntityType.as_view(versioning_class=scheme)
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_region(response)
        # search type region + ucode
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'entity_type': self.entity_type1.label,
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-type-and-ucode',
                    kwargs=kwargs) + '/?cached=False&geom=centroid'
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByEntityTypeAndUcode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_by_region_ucode(response)
        # test permission
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'entity_type': self.entity_type0.label
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-type', kwargs=kwargs)
        )
        view = ViewEntityListByEntityType.as_view(versioning_class=scheme)
        self._run_test_permission(request, view, **kwargs)
        # test permission - entity type + ucode
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'entity_type': self.entity_type1.label,
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-by-type-and-ucode',
                    kwargs=kwargs) + '/?cached=False&geom=centroid'
        )
        view = ViewEntityListByEntityTypeAndUcode.as_view(
            versioning_class=scheme
        )
        self._run_test_permission(request, view, **kwargs)

    def run_test_find_view_entity_versions(self):
        # search by concept uuid
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'concept_ucode': self.pak0_2.concept_ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-versions-by-concept-ucode',
                kwargs=kwargs
            )
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewFindEntityVersionsByConceptUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_versions_by_concept(response)
        # search by ucode
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-versions-by-ucode',
                kwargs=kwargs
            )
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewFindEntityVersionsByUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_versions_by_ucode_pak0_2(response)
        # search by ucode level 0 v1
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': self.pak0_1.ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-versions-by-ucode',
                kwargs=kwargs
            )
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewFindEntityVersionsByUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_versions_by_ucode_pak0_1(response)
        # search by ucode v1 level 1
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': self.entities_1[1].ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-versions-by-ucode',
                kwargs=kwargs
            )
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewFindEntityVersionsByUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_versions_by_ucode_entities1_1(response)
        # search by ucode and timestamp, at v2 daterange
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-versions-by-ucode',
                kwargs=kwargs
            ) + '/?timestamp=2023-01-11T06:16:13Z'
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewFindEntityVersionsByUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_versions_by_ucode_ts_v1(response)
        # search by ucode and timestamp, at v1 daterange
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-versions-by-ucode',
                kwargs=kwargs
            ) + '/?timestamp=2023-01-09T06:16:13Z'
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewFindEntityVersionsByUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_versions_by_ucode_ts_v2(response)
        # search by concept uuid and timestamp, at v1 daterange
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'concept_ucode': str(self.pak0_2.concept_ucode)
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-versions-by-concept-ucode',
                kwargs=kwargs
            ) + '/?timestamp=2023-01-09T06:16:13Z'
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewFindEntityVersionsByUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_versions_by_ucode_ts_v2(response)
        # test permission - concept uuid
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'concept_ucode': self.pak0_2.concept_ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-versions-by-concept-ucode',
                kwargs=kwargs
            )
        )
        view = ViewFindEntityVersionsByConceptUCode.as_view(
            versioning_class=scheme
        )
        self._run_test_permission(request, view, **kwargs)
        # test permission - ucode
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': self.entities_1[1].ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-versions-by-ucode',
                kwargs=kwargs
            )
        )
        view = ViewFindEntityVersionsByUCode.as_view(
            versioning_class=scheme
        )
        self._run_test_permission(request, view, **kwargs)
        # test permission - ucode + timestamp
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-versions-by-ucode',
                kwargs=kwargs
            ) + '/?timestamp=2023-01-09T06:16:13Z'
        )
        view = ViewFindEntityVersionsByUCode.as_view(
            versioning_class=scheme
        )
        self._run_test_permission(request, view, **kwargs)

    def run_test_view_entity_bbox(self):
        # found, by PCode = PAK
        pcode_0 = 'PAK'
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': 'PCode',
            'id': pcode_0
        }
        request = self.factory.get(
            reverse('v1:view-entity-bounding-box', kwargs=kwargs)
        )
        request.user = self.superuser
        view = ViewEntityBoundingBox.as_view()
        response = view(request, **kwargs)
        self.assert_view_entity_bbox_pcode_pak(response)
        # pcode is not found
        pcode_1 = 'PAK123'
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': 'PCode',
            'id': pcode_1
        }
        request = self.factory.get(
            reverse('v1:view-entity-bounding-box', kwargs=kwargs)
        )
        request.user = self.superuser
        view = ViewEntityBoundingBox.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        # invalid id
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': 'otherID',
            'id': pcode_1
        }
        request = self.factory.get(
            reverse('v1:view-entity-bounding-box', kwargs=kwargs)
        )
        request.user = self.superuser
        view = ViewEntityBoundingBox.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.data), 1)
        # search using UUID
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': 'uuid',
            'id': str(self.pak0_1.uuid_revision)
        }
        request = self.factory.get(
            reverse('v1:view-entity-bounding-box', kwargs=kwargs)
        )
        request.user = self.superuser
        view = ViewEntityBoundingBox.as_view()
        response = view(request, **kwargs)
        self.assert_view_entity_bbox_uuid_pak0_1(response)
        # test permission
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'id_type': 'uuid',
            'id': str(self.entities_2[2].uuid_revision)
        }
        request = self.factory.get(
            reverse('v1:view-entity-bounding-box', kwargs=kwargs)
        )
        self._run_test_permission(request, view, **kwargs)

    def run_test_view_entity_containment_check(self):
        # geojson data
        geojson_1_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'spatial_query_test_1.geojson')
        with open(geojson_1_path) as geojson:
            data_1 = json.load(geojson)
        geojson_2_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'spatial_query_test_2.geojson')
        with open(geojson_2_path) as geojson:
            data_2 = json.load(geojson)
        geojson_3_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'spatial_query_test_3.geojson')
        with open(geojson_3_path) as geojson:
            data_3 = json.load(geojson)
        geojson_4_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'spatial_query_test_4.geojson')
        with open(geojson_4_path) as geojson:
            data_4 = json.load(geojson)
        # ST_Intersects
        level_0 = 'Country'
        spatial_query_0 = 'ST_Intersects'
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': spatial_query_0,
            'distance': 0,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_1,
            format='json'
        )
        request.user = self.superuser
        view = ViewEntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_view_entity_containment_check_intersects(response)
        # no intersects
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_2,
            format='json'
        )
        request.user = self.superuser
        view = ViewEntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_view_entity_containment_check_intersects_not_found(
            response
        )
        # within found
        spatial_query_2 = 'ST_Within'
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': spatial_query_2,
            'distance': 0,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_3,
            format='json'
        )
        request.user = self.superuser
        view = ViewEntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_view_entity_containment_check_within_found(response)
        # dwithin
        spatial_query_3 = 'ST_DWithin'
        spatial_distance = 1
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': spatial_query_3,
            'distance': spatial_distance,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_2,
            format='json'
        )
        request.user = self.superuser
        view = ViewEntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_view_entity_containment_check_dwithin_found(response)
        # ST_Within(ST_Centroid)
        spatial_query_4 = 'ST_Within(ST_Centroid)'
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': spatial_query_4,
            'distance': 0,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_3,
            format='json'
        )
        request.user = self.superuser
        view = ViewEntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_view_entity_containment_check_within_centroid_found(
            response
        )
        # bad request
        spatial_query_5 = 'ST_Intersects'
        level_0_error = 'countrytest'
        kwargs_error = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': spatial_query_5,
            'distance': 0,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs_error
            ) + f'/?entity_type={level_0_error}',
            data=data_1,
            format='json'
        )
        request.user = self.superuser
        view = ViewEntityContainmentCheck.as_view()
        response = view(request, **kwargs_error)
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)
        # return hierarchy data in response
        spatial_query_2 = 'ST_Within'
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': spatial_query_2,
            'distance': 0,
            'id_type': 'ucode'
        }
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ),
            data=data_3,
            format='json'
        )
        request.user = self.superuser
        view = ViewEntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_view_entity_containment_check_hierarchy(response)
        # test 401
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': spatial_query_0,
            'distance': 0,
            'id_type': 'PCode'
        }
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_1,
            format='json'
        )
        request.user = None
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 401)
        # test 403 with user bob
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_1,
            format='json'
        )
        request.user = self.bob_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 403)
        # test with user moz level 3
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_1,
            format='json'
        )
        request.user = self.moz_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        # test with user dan and group viewer level 1
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ) + f'/?entity_type={level_0}',
            data=data_1,
            format='json'
        )
        request.user = self.dan_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        # test ST_Intersects ucode level 1, wrong result
        spatial_query_1 = 'ST_Intersects'
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'spatial_query': spatial_query_1,
            'distance': 0,
            'id_type': 'concept_ucode'
        }
        request = self.factory.post(
            reverse(
                'v1:view-entity-containment-check',
                kwargs=kwargs
            ) + '/?admin_level=1',
            data=data_4,
            format='json'
        )
        request.user = self.superuser
        view = ViewEntityContainmentCheck.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_view_entity_containment_check_intersects_cucode(response)

    def run_test_search_view_fuzzy_text(self):
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'search_text': 'paktan'
        }
        request = self.factory.get(
            reverse('v1:view-entity-fuzzy-search-by-name', kwargs=kwargs)
        )
        request.user = self.superuser
        view = ViewFindEntityFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        # test when 1 entity has two names (Pakistan and only paktang),
        # then only pull the name
        # with the highest similarity
        self.assert_view_entity_fuzzy_search_found1(response)
        entity_2 = GeographicalEntityF.create(
            dataset=self.dataset_view.dataset,
            type=self.entity_type0,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='PAK',
            revision_number=2,
            label='Pakistan',
            unique_code='PAK1',
            unique_code_version=1,
            start_date=isoparse('2023-01-01T06:16:13Z'),
            admin_level_name='Country',
            concept_ucode='#PAK_1'
        )
        EntityNameF.create(
            geographical_entity=entity_2,
            name=entity_2.label,
            idx=0
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=entity_2,
            default=True,
            value=entity_2.internal_code
        )
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'search_text': 'paki'
        }
        request = self.factory.get(
            reverse('v1:view-entity-fuzzy-search-by-name', kwargs=kwargs)
        )
        request.user = self.superuser
        view = ViewFindEntityFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        # search with paki, should return two diff results
        self.assert_view_entity_fuzzy_search_found2(response)
        # test permission
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'search_text': 'paktan'
        }
        request = self.factory.get(
            reverse('v1:view-entity-fuzzy-search-by-name', kwargs=kwargs)
        )
        self._run_test_permission(request, view, **kwargs)

    def run_test_search_view_fuzzy_geom(self):
        # geojson data
        geojson_1_path = absolute_path(
            'georepo', 'tests',
            'geojson_dataset', 'level_0.geojson')
        with open(geojson_1_path) as geojson:
            data_1 = json.load(geojson)
        kwargs = {
            'uuid': str(self.dataset_view.uuid)
        }
        request = self.factory.post(
            reverse(
                'v1:view-entity-fuzzy-search-by-geometry', kwargs=kwargs
            ),
            data=data_1,
            format='json'
        )
        request.user = self.superuser
        view = ViewFindEntityGeometryFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_view_entity_fuzzy_geom_search_found1(response)
        # invalid geojson
        request = self.factory.post(
            reverse(
                'v1:view-entity-fuzzy-search-by-geometry', kwargs=kwargs
            ),
            data={},
            format='json'
        )
        request.user = self.superuser
        view = ViewFindEntityGeometryFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 400)
        # search with level=2, return empty result
        request = self.factory.post(
            reverse(
                'v1:view-entity-fuzzy-search-by-geometry', kwargs=kwargs
            ) + '?admin_level=2',
            data=data_1,
            format='json'
        )
        request.user = self.superuser
        view = ViewFindEntityGeometryFuzzySearch.as_view()
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_view_entity_fuzzy_geom_search_level2(response)
        # test permission
        kwargs = {
            'uuid': str(self.dataset_view.uuid)
        }
        request = self.factory.post(
            reverse(
                'v1:view-entity-fuzzy-search-by-geometry', kwargs=kwargs
            ),
            data=data_1,
            format='json'
        )
        # test 401
        request.user = None
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 401)
        # test 403 with user bob
        request = self.factory.post(
            reverse(
                'v1:view-entity-fuzzy-search-by-geometry', kwargs=kwargs
            ),
            data=data_1,
            format='json'
        )
        request.user = self.bob_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 403)
        # test with user moz level 3
        request = self.factory.post(
            reverse(
                'v1:view-entity-fuzzy-search-by-geometry', kwargs=kwargs
            ),
            data=data_1,
            format='json'
        )
        request.user = self.moz_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        for item in response.data['results']:
            self.check_user_can_view_entity(item, self.moz_user)
        # test with user dan and group viewer level 1
        request = self.factory.post(
            reverse(
                'v1:view-entity-fuzzy-search-by-geometry', kwargs=kwargs
            ),
            data=data_1,
            format='json'
        )
        request.user = self.dan_user
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        for item in response.data['results']:
            self.check_user_can_view_entity(item, self.dan_user)

    def run_test_find_view_entity_parent_by_ucode(self):
        # search by ucode
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': 'PAK_0001_V2'
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-parent-by-ucode', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityTraverseHierarchyByUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_parent_by_ucode(response)
        # not found with ucode contains '/'
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': 'PA/K_0001_V2'
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-parent-by-ucode', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityTraverseHierarchyByUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        # test permission
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': 'PAK_0001_V2'
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-parent-by-ucode', kwargs=kwargs)
        )
        self._run_test_permission(request, view, **kwargs)

    def run_test_find_view_entity_children_by_ucode(self):
        # search by ucode
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-children-by-ucode', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityTraverseChildrenHierarchyByUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assert_find_view_entity_children_by_ucode(response)
        # not found with ucode contains '/'
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': 'PA/K_0001_V2'
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-children-by-ucode', kwargs=kwargs)
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityTraverseChildrenHierarchyByUCode.as_view(
            versioning_class=scheme
        )
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        # test permission
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse('v1:search-view-entity-children-by-ucode', kwargs=kwargs)
        )
        self._run_test_permission(request, view, **kwargs)

    def run_test_pagination(self):
        # useful to assert all entities are correctly returned
        kwargs = {
            'uuid': str(self.dataset_view.uuid),
            'admin_level': 1
        }
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-by-level',
                kwargs=kwargs
            ) + '?page=1&page_size=2'
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByAdminLevel.as_view(versioning_class=scheme)
        response1 = view(request, **kwargs)
        self.assertEqual(response1.status_code, 200)
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-by-level',
                kwargs=kwargs
            ) + '?page=2&page_size=2'
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByAdminLevel.as_view(versioning_class=scheme)
        response2 = view(request, **kwargs)
        self.assertEqual(response2.status_code, 200)
        request = self.factory.get(
            reverse(
                'v1:search-view-entity-by-level',
                kwargs=kwargs
            ) + '?page=3&page_size=2'
        )
        request.user = self.superuser
        scheme = versioning.NamespaceVersioning
        view = ViewEntityListByAdminLevel.as_view(versioning_class=scheme)
        response3 = view(request, **kwargs)
        self.assertEqual(response3.status_code, 200)
        self.assert_find_view_entity_by_level_paginated(
            [response1, response2, response3]
        )


class TestApiEntityLatestView(EntityViewTestSuite, TestCase):

    def setUp(self) -> None:
        self.call_setup()

    def generate_default_view(self):
        generate_default_view_dataset_latest(self.dataset)
        self.dataset_view = DatasetView.objects.filter(
            dataset=self.dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(self.dataset_view)
        # assign perm to user moz and group viewer level 1
        assign_perm('view_datasetview', self.moz_user, self.dataset_view)
        assign_perm('view_datasetview', self.viewer_1, self.dataset_view)

    def assert_find_view_entity_by_id_by_ucode(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_id_by_cucode(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_by_id_by_pcode(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_pcode_and_timestamp(self, response):
        self.assert_find_view_entity_by_id_by_pcode(response)

    def assert_find_view_entity_by_level_0(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_1(self, response):
        self.assertEqual(len(response.data['results']), 3)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_1_ucode(self, response):
        self.assertEqual(len(response.data['results']), 3)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['geometry'],
                            geom_type='centroid')
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['geometry'],
                            geom_type='centroid')
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['geometry'],
                            geom_type='centroid')

    def assert_find_view_entity_by_country(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_region(self, response):
        self.assert_find_view_entity_by_level_1(response)

    def assert_find_view_entity_by_region_ucode(self, response):
        self.assert_find_view_entity_by_level_1_ucode(response)

    def assert_find_view_entity_versions_by_concept(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_pak0_2(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_pak0_1(self, response):
        # search by ucode v1, found - because lvl 0 v2 exists in latest view
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_entities1_1(self, response):
        # search by ucode v1 level 1, not found, because v2, it's new concept
        self.assertEqual(len(response.data['results']), 0)

    def assert_find_view_entity_versions_by_ucode_ts_v1(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_ts_v2(self, response):
        self.assertEqual(len(response.data['results']), 0)

    def assert_view_entity_bbox_pcode_pak(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def assert_view_entity_bbox_uuid_pak0_1(self, response):
        self.assertEqual(response.status_code, 404)

    def assert_view_entity_containment_check_intersects(self, response):
        self.assertIn('PCode', response.data['features'][0]['properties'])
        pcodes_res = response.data['features'][0]['properties']['PCode']
        self.assertEqual(len(pcodes_res), 1)
        self.assertEqual(pcodes_res[0], 'PAK')

    def assert_view_entity_containment_check_intersects_cucode(self,
                                                               response):
        self.assertIn('concept_ucode',
                      response.data['features'][0]['properties'])

    def assert_view_entity_containment_check_intersects_not_found(self,
                                                                  response):
        self.assertNotIn('PCode', response.data['features'][0]['properties'])

    def assert_view_entity_containment_check_within_found(self, response):
        self.assertIn('PCode', response.data['features'][0]['properties'])
        pcodes_res = response.data['features'][0]['properties']['PCode']
        self.assertEqual(len(pcodes_res), 1)
        self.assertEqual(pcodes_res[0], 'PAK')

    def assert_view_entity_containment_check_dwithin_found(self, response):
        self.assertIn('PCode', response.data['features'][0]['properties'])
        pcodes_res = response.data['features'][0]['properties']['PCode']
        self.assertEqual(len(pcodes_res), 1)
        self.assertEqual(pcodes_res[0], 'PAK')

    def assert_view_entity_containment_check_within_centroid_found(self,
                                                                   response):
        self.assertIn('PCode', response.data['features'][0]['properties'])
        pcodes_res = response.data['features'][0]['properties']['PCode']
        self.assertEqual(len(pcodes_res), 1)
        self.assertEqual(pcodes_res[0], 'PAK')

    def assert_view_entity_containment_check_hierarchy(self, response):
        self.assertIn('ucode', response.data['features'][0]['properties'])

    def assert_view_entity_fuzzy_search_found1(self, response):
        # test when 1 entity has two names (Pakistan and only paktang),
        # then only pull the name
        # with the highest similarity
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_view_entity_fuzzy_search_found2(self, response):
        # search with paki, should return two diff results
        self.assertEqual(len(response.data['results']), 5)
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.pak0_2.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK1_V1']
        self.assertEqual(len(items), 1)

    def assert_view_entity_fuzzy_geom_search_found1(self, response):
        self.assertEqual(len(response.data['results']), 4)
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.pak0_2.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_view_entity_fuzzy_geom_search_level2(self, response):
        self.assertEqual(len(response.data['results']), 0)

    def assert_find_view_entity_parent_by_ucode(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_children_by_ucode(self, response):
        self.assert_find_view_entity_by_level_1(response)

    def test_find_view_entity_by_id(self):
        self.run_test_find_view_entity_by_id()

    def test_find_view_entity_by_level(self):
        self.run_test_find_view_entity_by_level()

    def test_find_view_entity_by_level_not_found(self):
        self.run_test_find_view_entity_by_level_not_found()

    def test_find_view_entity_by_type(self):
        self.run_test_find_view_entity_by_type()

    def test_find_view_entity_versions(self):
        self.run_test_find_view_entity_versions()

    def test_view_entity_bbox(self):
        self.run_test_view_entity_bbox()

    def test_view_entity_containment_check(self):
        self.run_test_view_entity_containment_check()

    @mock.patch.object(
        ViewFindEntityFuzzySearch, 'get_trigram_similarity',
        mock.Mock(return_value=0.45))
    def test_search_view_fuzzy_text(self):
        self.run_test_search_view_fuzzy_text()

    @mock.patch.object(
        ViewFindEntityGeometryFuzzySearch, 'get_simplify_tolerance',
        mock.Mock(return_value=0.08))
    def test_search_view_fuzzy_geom(self):
        self.run_test_search_view_fuzzy_geom()

    def test_find_view_entity_parent_by_ucode(self):
        self.run_test_find_view_entity_parent_by_ucode()

    def test_find_view_entity_children_by_ucode(self):
        self.run_test_find_view_entity_children_by_ucode()


class TestApiEntityAllVersionsView(EntityViewTestSuite, TestCase):

    def generate_default_view(self):
        generate_default_view_dataset_all_versions(self.dataset)
        self.dataset_view = DatasetView.objects.filter(
            dataset=self.dataset,
            default_type=DatasetView.DefaultViewType.ALL_VERSIONS,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(self.dataset_view)
        # assign perm to user moz and group viewer level 1
        assign_perm('view_datasetview', self.moz_user, self.dataset_view)
        assign_perm('view_datasetview', self.viewer_1, self.dataset_view)

    def setUp(self) -> None:
        self.call_setup()

    def assert_find_view_entity_by_id_by_ucode(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_id_by_cucode(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_by_id_by_pcode(self, response):
        # find by pcode PAK001 should return both versions
        self.assertEqual(len(response.data['results']), 2)
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.entities_1[0].ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_1[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.entities_2[0].ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_pcode_and_timestamp(self, response):
        # find by pcode PAK001 with timestamp should return the latest
        self.assertEqual(len(response.data['results']), 1)
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.entities_2[0].ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_0(self, response):
        # search by level 0, should return both versions
        self.assertEqual(len(response.data['results']), 2)
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.pak0_1.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.pak0_1,
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.pak0_2.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_1(self, response):
        # should return 2 entities from rev1, 3 entities from rev2
        self.assertEqual(len(response.data['results']), 5)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V1']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_1[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V1']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_1[1],
                            excluded_columns=['centroid', 'geometry'])
        # revision 2
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_1_ucode(self, response):
        # find by level 1 and parent ucode from pak0_2, should return 3
        self.assertEqual(len(response.data['results']), 3)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['geometry'],
                            geom_type='centroid')
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['geometry'],
                            geom_type='centroid')
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['geometry'],
                            geom_type='centroid')

    def assert_find_view_entity_by_country(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_by_region(self, response):
        self.assert_find_view_entity_by_level_1(response)

    def assert_find_view_entity_by_region_ucode(self, response):
        self.assert_find_view_entity_by_level_1_ucode(response)

    def assert_find_view_entity_versions_by_concept(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_versions_by_ucode_pak0_2(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_versions_by_ucode_pak0_1(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_versions_by_ucode_entities1_1(self, response):
        # search by ucode from rev 1 level 1
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.entities_1[1],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_ts_v1(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_ts_v2(self, response):
        # search by ucode and timestamp, at v1 daterange, should return 1
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_1,
                            excluded_columns=['centroid', 'geometry'])

    def assert_view_entity_bbox_pcode_pak(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def assert_view_entity_bbox_uuid_pak0_1(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def assert_find_view_entity_by_level_paginated(self, responses):
        self.assertEqual(len(responses), 3)
        # response0 should contain 2
        response0 = responses[0]
        self.assertEqual(len(response0.data['results']), 2)
        items = [x for x in response0.data['results'] if
                 x['ucode'] == 'PAK_0001_V1']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_1[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response0.data['results'] if
                 x['ucode'] == 'PAK_0002_V1']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_1[1],
                            excluded_columns=['centroid', 'geometry'])
        # response1 should contain 2
        response1 = responses[1]
        self.assertEqual(len(response1.data['results']), 2)
        items = [x for x in response1.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response1.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['centroid', 'geometry'])
        # response2 should contain 1
        response2 = responses[2]
        self.assertEqual(len(response2.data['results']), 1)
        items = [x for x in response2.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['centroid', 'geometry'])

    def assert_view_entity_containment_check_intersects(self, response):
        self.assertIn('PCode', response.data['features'][0]['properties'])
        pcodes_res = response.data['features'][0]['properties']['PCode']
        self.assertEqual(len(pcodes_res), 2)
        self.assertEqual(pcodes_res[0], 'PAK')

    def assert_view_entity_containment_check_within_found(self, response):
        self.assert_view_entity_containment_check_intersects(response)

    def assert_view_entity_containment_check_dwithin_found(self, response):
        self.assert_view_entity_containment_check_intersects(response)

    def assert_view_entity_containment_check_within_centroid_found(self,
                                                                   response):
        self.assert_view_entity_containment_check_intersects(response)

    def assert_view_entity_containment_check_hierarchy(self, response):
        self.assertIn('ucode', response.data['features'][0]['properties'])

    def assert_view_entity_containment_check_intersects_cucode(self,
                                                               response):
        self.assertIn('concept_ucode',
                      response.data['features'][0]['properties'])

    def assert_view_entity_containment_check_intersects_not_found(self,
                                                                  response):
        self.assertNotIn('PCode', response.data['features'][0]['properties'])

    def test_find_view_entity_by_id(self):
        self.run_test_find_view_entity_by_id()

    def test_find_view_entity_by_level(self):
        self.run_test_find_view_entity_by_level()

    def test_find_view_entity_by_type(self):
        self.run_test_find_view_entity_by_type()

    def test_find_view_entity_versions(self):
        self.run_test_find_view_entity_versions()

    def test_view_entity_bbox(self):
        self.run_test_view_entity_bbox()

    def test_view_entity_containment_check(self):
        self.run_test_view_entity_containment_check()

    def test_pagination_level1(self):
        self.run_test_pagination()


class TestApiEntityAdm0LatestView(EntityViewTestSuite, TestCase):

    def setUp(self) -> None:
        self.call_setup()

    def generate_default_view(self):
        # add other adm0
        sy0_1 = GeographicalEntityF.create(
            dataset=self.dataset,
            level=0,
            admin_level_name='Country',
            type=self.entity_type0,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='SY',
            revision_number=1,
            label='Syria',
            unique_code='SY',
            unique_code_version=1,
            start_date=isoparse('2023-01-01T06:16:13Z'),
            end_date=isoparse('2023-01-10T06:16:13Z'),
            concept_ucode='#SY_1'
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=sy0_1,
            default=True,
            value=sy0_1.internal_code
        )
        EntityNameF.create(
            geographical_entity=sy0_1,
            name=sy0_1.label,
            language=self.enLang,
            idx=0
        )
        entity = GeographicalEntityF.create(
            parent=sy0_1,
            ancestor=sy0_1,
            level=1,
            admin_level_name='Region',
            dataset=self.dataset,
            type=self.entity_type1,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='SY001',
            revision_number=1,
            label='SY region1',
            unique_code='SY_0001',
            unique_code_version=1,
            start_date=isoparse('2023-01-01T06:16:13Z'),
            end_date=isoparse('2023-01-10T06:16:13Z'),
            concept_ucode='#SY_2'
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=entity,
            default=True,
            value=entity.internal_code
        )
        EntityNameF.create(
            geographical_entity=entity,
            name=entity.label,
            language=self.enLang,
            idx=0
        )
        generate_default_view_adm0_latest(self.dataset)
        self.dataset_view = DatasetView.objects.filter(
            dataset=self.dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code=self.pak0_2.unique_code
        ).first()
        init_view_privacy_level(self.dataset_view)
        # assign perm to user moz and group viewer level 1
        assign_perm('view_datasetview', self.moz_user, self.dataset_view)
        assign_perm('view_datasetview', self.viewer_1, self.dataset_view)

    def assert_find_view_entity_by_id_by_ucode(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_id_by_cucode(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_by_id_by_pcode(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_pcode_and_timestamp(self, response):
        self.assert_find_view_entity_by_id_by_pcode(response)

    def assert_find_view_entity_by_level_0(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_1(self, response):
        self.assertEqual(len(response.data['results']), 3)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_1_ucode(self, response):
        self.assertEqual(len(response.data['results']), 3)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['geometry'],
                            geom_type='centroid')
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['geometry'],
                            geom_type='centroid')
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['geometry'],
                            geom_type='centroid')

    def assert_find_view_entity_by_country(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_region(self, response):
        self.assertEqual(len(response.data['results']), 3)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_region_ucode(self, response):
        self.assert_find_view_entity_by_level_1_ucode(response)

    def assert_find_view_entity_versions_by_concept(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_pak0_2(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_pak0_1(self, response):
        # search by ucode v1, found - because lvl 0 v2 exists in latest view
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_entities1_1(self, response):
        # search by ucode v1 level 1, not found, because v2, it's new concept
        self.assertEqual(len(response.data['results']), 0)

    def assert_find_view_entity_versions_by_ucode_ts_v1(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_ts_v2(self, response):
        self.assertEqual(len(response.data['results']), 0)

    def assert_view_entity_bbox_pcode_pak(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def assert_view_entity_bbox_uuid_pak0_1(self, response):
        self.assertEqual(response.status_code, 404)

    def test_find_view_entity_by_id(self):
        self.run_test_find_view_entity_by_id()

    def test_find_view_entity_by_level(self):
        self.run_test_find_view_entity_by_level()

    def test_find_view_entity_by_type(self):
        self.run_test_find_view_entity_by_type()

    def test_find_view_entity_versions(self):
        self.run_test_find_view_entity_versions()

    def test_view_entity_bbox(self):
        return self.run_test_view_entity_bbox()


class TestApiEntityAdm0AllVersionsView(EntityViewTestSuite, TestCase):

    def generate_default_view(self):
        # add other adm0
        sy0_1 = GeographicalEntityF.create(
            dataset=self.dataset,
            level=0,
            admin_level_name='Country',
            type=self.entity_type0,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='SY',
            revision_number=1,
            label='Syria',
            unique_code='SY',
            unique_code_version=1,
            start_date=isoparse('2023-01-01T06:16:13Z'),
            end_date=isoparse('2023-01-10T06:16:13Z'),
            concept_ucode='#SY_1'
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=sy0_1,
            default=True,
            value=sy0_1.internal_code
        )
        EntityNameF.create(
            geographical_entity=sy0_1,
            name=sy0_1.label,
            language=self.enLang,
            idx=0
        )
        entity = GeographicalEntityF.create(
            parent=sy0_1,
            ancestor=sy0_1,
            level=1,
            admin_level_name='Region',
            dataset=self.dataset,
            type=self.entity_type1,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='SY001',
            revision_number=1,
            label='SY region1',
            unique_code='SY_0001',
            unique_code_version=1,
            start_date=isoparse('2023-01-01T06:16:13Z'),
            end_date=isoparse('2023-01-10T06:16:13Z'),
            concept_ucode='#SY_2'
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=entity,
            default=True,
            value=entity.internal_code
        )
        EntityNameF.create(
            geographical_entity=entity,
            name=entity.label,
            language=self.enLang,
            idx=0
        )
        generate_default_view_adm0_all_versions(self.dataset)
        self.dataset_view = DatasetView.objects.filter(
            dataset=self.dataset,
            default_type=DatasetView.DefaultViewType.ALL_VERSIONS,
            default_ancestor_code=self.pak0_2.unique_code
        ).first()
        init_view_privacy_level(self.dataset_view)
        # assign perm to user moz and group viewer level 1
        assign_perm('view_datasetview', self.moz_user, self.dataset_view)
        assign_perm('view_datasetview', self.viewer_1, self.dataset_view)

    def setUp(self) -> None:
        self.call_setup()

    def assert_find_view_entity_by_id_by_ucode(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_id_by_cucode(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_by_id_by_pcode(self, response):
        # find by pcode PAK001 should return both versions
        self.assertEqual(len(response.data['results']), 2)
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.entities_1[0].ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_1[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.entities_2[0].ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_pcode_and_timestamp(self, response):
        # find by pcode PAK001 should return latest
        self.assertEqual(len(response.data['results']), 1)
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.entities_2[0].ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_0(self, response):
        # search by level 0, should return both versions
        self.assertEqual(len(response.data['results']), 2)
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.pak0_1.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.pak0_1,
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == self.pak0_2.ucode]
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_1(self, response):
        # should return 2 entities from rev1, 3 entities from rev2
        self.assertEqual(len(response.data['results']), 5)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V1']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_1[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V1']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_1[1],
                            excluded_columns=['centroid', 'geometry'])
        # revision 2
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_1_ucode(self, response):
        # find by level 1 and parent ucode from pak0_2, should return 3
        self.assertEqual(len(response.data['results']), 3)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['geometry'],
                            geom_type='centroid')
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['geometry'],
                            geom_type='centroid')
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['geometry'],
                            geom_type='centroid')

    def assert_find_view_entity_by_country(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_by_region(self, response):
        self.assert_find_view_entity_by_level_1(response)

    def assert_find_view_entity_by_region_ucode(self, response):
        self.assert_find_view_entity_by_level_1_ucode(response)

    def assert_find_view_entity_versions_by_concept(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_versions_by_ucode_pak0_2(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_versions_by_ucode_pak0_1(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_versions_by_ucode_entities1_1(self, response):
        # search by ucode from rev 1 level 1
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.entities_1[1],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_ts_v1(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_ts_v2(self, response):
        # search by ucode and timestamp, at v1 daterange, should return 1
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_1,
                            excluded_columns=['centroid', 'geometry'])

    def assert_view_entity_bbox_pcode_pak(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def assert_view_entity_bbox_uuid_pak0_1(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def test_find_view_entity_by_id(self):
        self.run_test_find_view_entity_by_id()

    def test_find_view_entity_by_level(self):
        self.run_test_find_view_entity_by_level()

    def test_find_view_entity_by_type(self):
        self.run_test_find_view_entity_by_type()

    def test_find_view_entity_versions(self):
        self.run_test_find_view_entity_versions()

    def test_view_entity_bbox(self):
        return self.run_test_view_entity_bbox()


class TestApiEntityStaticView(EntityViewTestSuite, TestCase):

    def setUp(self) -> None:
        self.call_setup()
        # test add new entities
        entity = GeographicalEntityF.create(
            parent=self.pak0_2,
            ancestor=self.pak0_2,
            level=1,
            admin_level_name='Region',
            dataset=self.dataset,
            type=self.entity_type1,
            is_validated=True,
            is_approved=True,
            is_latest=True,
            internal_code='PAK099',
            revision_number=2,
            label='PAK099 region1',
            unique_code='PAK_0099',
            unique_code_version=2,
            start_date=isoparse('2023-01-10T06:16:13Z'),
            concept_ucode='PAK_100'
        )
        EntityIdF.create(
            code=self.pCode,
            geographical_entity=entity,
            default=True,
            value=entity.internal_code
        )
        EntityNameF.create(
            geographical_entity=entity,
            name=entity.label,
            language=self.enLang,
            idx=0
        )
        # test second name without language
        EntityNameF.create(
            geographical_entity=entity,
            name=entity.label,
            idx=1
        )

    def generate_default_view(self):
        sql = (
            'select * from georepo_geographicalentity '
            f'where dataset_id={self.dataset.id} '
            'and is_approved=true and is_latest=true;'
        )
        self.dataset_view = DatasetView.objects.create(
            name='Test Static',
            description='Test Static',
            dataset=self.dataset,
            is_static=True,
            query_string=sql
        )
        create_sql_view(self.dataset_view)
        init_view_privacy_level(self.dataset_view)
        # assign perm to user moz and group viewer level 1
        assign_perm('view_datasetview', self.moz_user, self.dataset_view)
        assign_perm('view_datasetview', self.viewer_1, self.dataset_view)

    def assert_find_view_entity_by_id_by_ucode(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_id_by_cucode(self, response):
        self.assert_find_view_entity_by_level_0(response)

    def assert_find_view_entity_by_id_by_pcode(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_pcode_and_timestamp(self, response):
        self.assert_find_view_entity_by_id_by_pcode(response)

    def assert_find_view_entity_by_level_0(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_1(self, response):
        self.assertEqual(len(response.data['results']), 3)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['centroid', 'geometry'])
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_level_1_ucode(self, response):
        self.assertEqual(len(response.data['results']), 3)
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0001_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[0],
                            excluded_columns=['geometry'],
                            geom_type='centroid')
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0002_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[1],
                            excluded_columns=['geometry'],
                            geom_type='centroid')
        items = [x for x in response.data['results'] if
                 x['ucode'] == 'PAK_0003_V2']
        self.assertEqual(len(items), 1)
        self.check_response(items[0],
                            self.entities_2[2],
                            excluded_columns=['geometry'],
                            geom_type='centroid')

    def assert_find_view_entity_by_country(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_by_region(self, response):
        self.assert_find_view_entity_by_level_1(response)

    def assert_find_view_entity_by_region_ucode(self, response):
        self.assert_find_view_entity_by_level_1_ucode(response)

    def assert_find_view_entity_versions_by_concept(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_pak0_2(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_pak0_1(self, response):
        # search by ucode v1, found - because lvl 0 v2 exists in latest view
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_entities1_1(self, response):
        # search by ucode v1 level 1, not found, because v2, it's new concept
        self.assertEqual(len(response.data['results']), 0)

    def assert_find_view_entity_versions_by_ucode_ts_v1(self, response):
        self.assertEqual(len(response.data['results']), 1)
        self.check_response(response.data['results'][0],
                            self.pak0_2,
                            excluded_columns=['centroid', 'geometry'])

    def assert_find_view_entity_versions_by_ucode_ts_v2(self, response):
        self.assertEqual(len(response.data['results']), 0)

    def test_find_view_entity_by_id(self):
        self.run_test_find_view_entity_by_id()

    def test_find_view_entity_by_level(self):
        self.run_test_find_view_entity_by_level()

    def test_find_view_entity_by_type(self):
        self.run_test_find_view_entity_by_type()

    def test_find_view_entity_versions(self):
        self.run_test_find_view_entity_versions()


class TestApiFindEntity(EntityResponseChecker, BaseDatasetViewTest):

    def setUp(self):
        super().setUp()
        # create user 1 has privacy level 4 at dataset
        self.user_1 = UserF.create()
        grant_dataset_viewer(self.dataset, self.user_1, 4)
        # create user 2 has privacy level 3 at dataset
        self.user_2 = UserF.create()
        grant_dataset_viewer(self.dataset, self.user_2, 3)
        # create user 3 has external permission at custom view
        self.user_3 = UserF.create()
        # create user 4 does not have permission at all
        self.user_4 = UserF.create()
        sql = (
            'select * from georepo_geographicalentity '
            f'where dataset_id={self.dataset.id} '
            'and is_approved=true and is_latest=true and level=0;'
        )
        self.custom_view = DatasetView.objects.create(
            name='Test Custom View',
            description='Test Custom View',
            dataset=self.dataset,
            is_static=False,
            query_string=sql
        )
        create_sql_view(self.custom_view)
        init_view_privacy_level(self.custom_view)
        calculate_entity_count_in_view(self.custom_view)
        grant_datasetview_external_viewer(self.custom_view, self.user_3, 4)
        # generate latest for countries
        generate_default_view_adm0_latest(self.dataset)
        self.country_view = DatasetView.objects.filter(
            dataset=self.dataset,
            default_type=DatasetView.DefaultViewType.IS_LATEST,
            default_ancestor_code=self.pak0_2.unique_code
        ).first()
        init_view_privacy_level(self.country_view)
        calculate_entity_count_in_view(self.country_view)

    def check_view_in_response(self, item: dict, view: DatasetView):
        self.assertIn('views', item)
        views = item['views']
        find_item = [v for v in views if v['uuid'] == str(view.uuid)]
        self.assertTrue(len(find_item) > 0)

    def test_find_entity_by_ucode_not_found(self):
        view = FindEntityByUCode.as_view()
        kwargs = {
            'ucode': 'TEST_EMPTY_V1'
        }
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-ucode',
                kwargs=kwargs
            ),
        )
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        # user_2 should not be able to view the entity
        kwargs = {
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-ucode',
                kwargs=kwargs
            ),
        )
        request.user = self.user_2
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        # user_4 should not be able to view at all
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-ucode',
                kwargs=kwargs
            ),
        )
        request.user = self.user_4
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)

    def test_find_entity_by_ucode(self):
        view = FindEntityByUCode.as_view()
        kwargs = {
            'ucode': self.pak0_2.ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-ucode',
                kwargs=kwargs
            ),
        )
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.check_response(response.data, self.pak0_2)
        self.check_user_can_view_entity(response.data, self.superuser)
        self.check_view_in_response(response.data, self.dataset_view)
        self.check_view_in_response(response.data, self.custom_view)
        self.check_view_in_response(response.data, self.country_view)
        self.assertEqual(len(response.data['views']), 3)
        # test using user 1, should have access
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-ucode',
                kwargs=kwargs
            ),
        )
        request.user = self.user_1
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.check_response(response.data, self.pak0_2)
        self.check_user_can_view_entity(response.data, self.user_1)
        self.check_view_in_response(response.data, self.dataset_view)
        self.check_view_in_response(response.data, self.custom_view)
        self.check_view_in_response(response.data, self.country_view)
        self.assertEqual(len(response.data['views']), 3)
        # test using user 3, should have access to only custom_view
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-ucode',
                kwargs=kwargs
            ),
        )
        request.user = self.user_3
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.check_response(response.data, self.pak0_2)
        self.check_user_can_view_entity_in_view(
            response.data, self.user_3, self.custom_view)
        self.check_view_in_response(response.data, self.custom_view)
        self.assertEqual(len(response.data['views']), 1)

    def test_find_entity_by_ucode_in_prev_version(self):
        # generate all versions view
        generate_default_view_dataset_all_versions(self.dataset)
        all_versions_view = DatasetView.objects.filter(
            dataset=self.dataset,
            default_type=DatasetView.DefaultViewType.ALL_VERSIONS,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(all_versions_view)
        calculate_entity_count_in_view(all_versions_view)
        view = FindEntityByUCode.as_view()
        kwargs = {
            'ucode': self.pak0_1.ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-ucode',
                kwargs=kwargs
            ),
        )
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.check_response(response.data, self.pak0_1)
        self.check_user_can_view_entity(response.data, self.superuser)
        self.check_view_in_response(response.data, all_versions_view)
        self.assertEqual(len(response.data['views']), 1)

    def test_find_entity_by_cucode_not_found(self):
        view = FindEntityByCUCode.as_view()
        kwargs = {
            'cucode': '#TEST_EMPTY_V1'
        }
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-cucode',
                kwargs=kwargs
            ),
        )
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        # user_2 should not be able to view the entity
        kwargs = {
            'cucode': self.pak0_2.concept_ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-cucode',
                kwargs=kwargs
            ),
        )
        request.user = self.user_2
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)
        # user_4 should not be able to view at all
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-cucode',
                kwargs=kwargs
            ),
        )
        request.user = self.user_4
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 404)

    def test_find_entity_by_cucode(self):
        view = FindEntityByCUCode.as_view()
        kwargs = {
            'cucode': self.pak0_2.concept_ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-cucode',
                kwargs=kwargs
            ),
        )
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.check_response(response.data[0], self.pak0_2)
        self.check_user_can_view_entity(response.data[0], self.superuser)
        self.assertEqual(len(response.data[0]['views']), 3)
        self.check_view_in_response(response.data[0], self.dataset_view)
        self.check_view_in_response(response.data[0], self.custom_view)
        self.check_view_in_response(response.data[0], self.country_view)
        # test using user 1, should have access
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-cucode',
                kwargs=kwargs
            ),
        )
        request.user = self.user_1
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.check_response(response.data[0], self.pak0_2)
        self.check_user_can_view_entity(response.data[0], self.superuser)
        self.assertEqual(len(response.data[0]['views']), 3)
        self.check_view_in_response(response.data[0], self.dataset_view)
        self.check_view_in_response(response.data[0], self.custom_view)
        self.check_view_in_response(response.data[0], self.country_view)
        # test using user 3, should have access to only custom_view
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-cucode',
                kwargs=kwargs
            ),
        )
        request.user = self.user_3
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.check_response(response.data[0], self.pak0_2)
        self.check_user_can_view_entity_in_view(
            response.data[0], self.user_3, self.custom_view)
        self.check_view_in_response(response.data[0], self.custom_view)
        self.assertEqual(len(response.data[0]['views']), 1)

    def test_find_entity_by_cucode_in_prev_version(self):
        # generate all versions view
        generate_default_view_dataset_all_versions(self.dataset)
        all_versions_view = DatasetView.objects.filter(
            dataset=self.dataset,
            default_type=DatasetView.DefaultViewType.ALL_VERSIONS,
            default_ancestor_code__isnull=True
        ).first()
        init_view_privacy_level(all_versions_view)
        calculate_entity_count_in_view(all_versions_view)
        view = FindEntityByCUCode.as_view()
        kwargs = {
            'cucode': self.pak0_1.concept_ucode
        }
        request = self.factory.get(
            reverse(
                'v1:search-entity-by-cucode',
                kwargs=kwargs
            ),
        )
        request.user = self.superuser
        response = view(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.check_response(response.data[0], self.pak0_1)
        self.check_user_can_view_entity(response.data[0], self.superuser)
        self.check_view_in_response(response.data[0], all_versions_view)
        self.assertEqual(len(response.data[0]['views']), 1)
        self.check_response(response.data[1], self.pak0_2)
        self.check_user_can_view_entity(response.data[1], self.superuser)
        self.assertEqual(len(response.data[1]['views']), 4)
        self.check_view_in_response(response.data[1], self.dataset_view)
        self.check_view_in_response(response.data[1], self.custom_view)
        self.check_view_in_response(response.data[1], self.country_view)
        self.check_view_in_response(response.data[1], all_versions_view)

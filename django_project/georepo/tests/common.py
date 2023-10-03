from georepo.models.entity import GeographicalEntity
from georepo.utils.permission import get_view_permission_privacy_level


class EntityResponseChecker(object):

    def check_response(self, item: dict, geo: GeographicalEntity,
                       excluded_columns=[], geom_type=None, user=None):
        self.assertEqual(
            item['name'],
            geo.label
        )
        self.assertEqual(
            item['ucode'],
            geo.ucode
        )
        self.assertIn(
            'concept_ucode',
            item
        )
        self.assertEqual(
            item['concept_ucode'],
            geo.concept_ucode
        )
        self.assertEqual(
            item['uuid'],
            geo.uuid_revision
        )
        self.assertEqual(
            item['concept_uuid'],
            geo.uuid
        )
        self.assertEqual(
            item['admin_level'],
            geo.level
        )
        if geo.admin_level_name:
            self.assertEqual(
                item['level_name'],
                geo.admin_level_name
            )
        else:
            self.assertNotIn(
                'level_name',
                item
            )
        self.assertEqual(
            item['type'],
            geo.type.label
        )
        self.assertEqual(
            item['start_date'],
            geo.start_date.isoformat()
        )
        if geo.end_date:
            self.assertEqual(
                item['end_date'],
                geo.end_date.isoformat()
            )
        else:
            self.assertNotIn(
                'end_date',
                item
            )
        self.assertIn('ext_codes', item)
        self.assertTrue(len(item['ext_codes'].keys()) > 0)
        self.assertEqual(
            item['ext_codes']['default'],
            geo.internal_code
        )
        entity_ids = geo.entity_ids.all()
        for entity_id in entity_ids:
            self.assertIn(
                entity_id.code.name,
                item['ext_codes']
            )
            self.assertEqual(
                item['ext_codes'][entity_id.code.name],
                entity_id.value
            )
        self.assertIn('names', item)
        self.assertEqual(len(item['names']), geo.entity_names.count())
        entity_names = geo.entity_names.order_by('idx').all()
        for entity_name in entity_names:
            name = [x for x in item['names'] if
                    x['name'] == entity_name.name]
            self.assertTrue(len(name) > 0)
            name = name[0]
            if entity_name.label:
                self.assertIn(
                    'label',
                    name
                )
                self.assertEqual(
                    entity_name.label,
                    name['label']
                )
            if entity_name.language:
                self.assertIn(
                    'lang',
                    name
                )
                self.assertEqual(
                    entity_name.language.code,
                    name['lang']
                )
        self.assertEqual(
            item['is_latest'],
            geo.is_latest
        )
        self.assertIn('parents', item)
        self.assertEqual(len(item['parents']), geo.level)
        if geo.parent:
            parent = geo.parent
            while parent:
                item_parents = [x for x in item['parents'] if
                                x['ucode'] == parent.ucode]
                self.assertEqual(len(item_parents), 1)
                item_parent = item_parents[0]
                self.assertEqual(parent.ucode, item_parent['ucode'])
                self.assertEqual(parent.internal_code, item_parent['default'])
                self.assertEqual(parent.level, item_parent['admin_level'])
                self.assertEqual(parent.type.label, item_parent['type'])
                parent = parent.parent
        if 'bbox' in item:
            self.assertEqual(len(item['bbox']), 4)
        for col in excluded_columns:
            self.assertNotIn(col, item)
        if geom_type == 'centroid':
            self.assertIn('centroid', item)
        if geom_type == 'geometry':
            self.assertIn('geometry', item)
        if user:
            self.check_user_can_view_entity(item, user)

    def check_user_can_view_entity(self, item: dict, user):
        """
        Test whether user can view entity with current permission level.
        """
        self.assertIn('uuid', item)
        geo = GeographicalEntity.objects.get(uuid_revision=item['uuid'])
        max_privacy_level = get_view_permission_privacy_level(user,
                                                              geo.dataset)
        self.assertGreaterEqual(max_privacy_level, geo.privacy_level)

    def check_user_can_view_entity_in_view(self, item: dict,
                                           user, dataset_view):
        """
        Test whether user can view entity.

        This also considers external user permission in dataset_view
        """
        self.assertIn('uuid', item)
        geo = GeographicalEntity.objects.get(uuid_revision=item['uuid'])
        max_privacy_level = get_view_permission_privacy_level(
            user,
            geo.dataset,
            dataset_view=dataset_view
        )
        self.assertGreaterEqual(max_privacy_level, geo.privacy_level)

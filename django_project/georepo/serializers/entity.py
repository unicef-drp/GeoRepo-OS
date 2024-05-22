from collections import OrderedDict
import json
import ast
from rest_framework import serializers
from drf_yasg import openapi
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.contrib.gis.geos import GEOSGeometry
from georepo.serializers.common import APIResponseModelSerializer
from georepo.models import GeographicalEntity
from georepo.utils.unique_code import get_unique_code
from georepo.utils.entity_query import normalize_attribute_name


class GeographicalEntitySerializer(APIResponseModelSerializer):
    # simple, geojson
    output_format = 'simple'

    ucode = serializers.SerializerMethodField()
    uuid = serializers.SerializerMethodField()
    concept_uuid = serializers.SerializerMethodField()
    concept_ucode = serializers.SerializerMethodField()
    is_latest = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    admin_level = serializers.SerializerMethodField()
    level_name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    ext_codes = serializers.SerializerMethodField()
    names = serializers.SerializerMethodField()
    bbox = serializers.SerializerMethodField()
    centroid = serializers.SerializerMethodField()
    geometry = serializers.SerializerMethodField()
    parents = serializers.SerializerMethodField()

    def get_centroid(self, obj: GeographicalEntity):
        try:
            return obj['centroid']
        except KeyError:
            return None

    def get_bbox(self, obj: GeographicalEntity):
        if self.output_format != 'simple':
            return None
        if obj['bbox']:
            return ast.literal_eval(obj['bbox'])
        return None

    def get_geometry(self, obj: GeographicalEntity):
        if 'rhr_geom' in obj and obj['rhr_geom']:
            geom = GEOSGeometry(obj['rhr_geom'])
            return json.loads(geom.geojson)
        return None

    def get_ucode(self, obj: GeographicalEntity):
        code = obj.get('unique_code', '')
        version = obj.get('unique_code_version', 1)
        return get_unique_code(code, version)

    def get_uuid(self, obj: GeographicalEntity):
        return obj.get('uuid_revision', '')

    def get_concept_uuid(self, obj: GeographicalEntity):
        return obj.get('uuid', '')

    def get_concept_ucode(self, obj: GeographicalEntity):
        return obj.get('concept_ucode', '')

    def get_is_latest(self, obj: GeographicalEntity):
        return obj.get('is_latest', '')

    def get_start_date(self, obj: GeographicalEntity):
        start_date = obj.get('start_date', None)
        if start_date:
            start_date = start_date.isoformat()
        return start_date

    def get_end_date(self, obj: GeographicalEntity):
        end_date = obj.get('end_date', None)
        if end_date:
            end_date = end_date.isoformat()
        return end_date

    def get_name(self, obj: GeographicalEntity):
        return obj.get('label', '')

    def get_level_name(self, obj: GeographicalEntity):
        return obj.get('admin_level_name', '')

    def get_admin_level(self, obj: GeographicalEntity):
        return obj.get('level', '')

    def get_type(self, obj: GeographicalEntity):
        return obj.get('type__label', '')

    def get_ext_codes(self, obj: GeographicalEntity):
        ids = (
            self.context['ids'] if 'ids' in self.context
            else []
        )
        if len(ids) == 0:
            return {
                'default': obj.get('internal_code', '')
            }
        identifiers = {}
        # find default
        default_code = None
        for id in ids:
            field_key = f"id_{id['code__id']}__value"
            val = obj.get(field_key, None)
            if val:
                if id['default']:
                    default_code = val
                identifiers[id['code__name']] = val
            elif self.output_format == 'geojson':
                identifiers[id['code__name']] = None
        if default_code:
            identifiers['default'] = default_code
        elif self.output_format == 'geojson':
            identifiers['default'] = obj.get('internal_code', '')
        if 'default' not in identifiers:
            identifiers['default'] = obj.get('internal_code', '')
        return identifiers

    def get_names(self, obj: GeographicalEntity):
        names_max_idx = (
            self.context['names'] if 'names' in self.context
            else None
        )
        if names_max_idx is None or names_max_idx['idx__max'] is None:
            return []
        names = []
        default_lang_code = 'EN'
        # find the count of name having same lang that does not have label
        # e.g. name_1 (EN) = 'abc', name_2 (EN) = 'def'
        # the resulting labels would be 'name_en_1' and 'name_en_2'
        # when there is only 1 lang, then the resulting label would be:
        # e.g. 'name_en'
        name_labels_dict = {}
        for name_idx in range(names_max_idx['idx__max'] + 1):
            field_key = f"name_{name_idx}"
            val = obj.get(f'{field_key}__name', None)
            if val is None or val == '':
                continue
            lang = obj.get(f'{field_key}__language__code', default_lang_code)
            if lang is None:
                lang = default_lang_code
            label = obj.get(f'{field_key}__label', None)
            name_label = ''
            if label:
                name_label = '{label}'.format(
                    label=label
                )
            else:
                name_label = f'name_{lang.lower()}'
            if name_label in name_labels_dict:
                name_labels_dict[name_label]['total'] += 1
                name_labels_dict[name_label]['values'].append(val)
                name_labels_dict[name_label]['langs'].append(lang)
            else:
                name_labels_dict[name_label] = {
                    'total': 1,
                    'values': [val],
                    'langs': [lang]
                }
        for name_label, values in name_labels_dict.items():
            if values['total'] == 1:
                name = {
                    'name': values['values'][0],
                    'lang': values['langs'][0],
                    'label': name_label
                }
                names.append(name)
            else:
                for idx, value in enumerate(values['values']):
                    name = {
                        'name': value,
                        'lang': values['langs'][idx],
                        'label': normalize_attribute_name(
                            name_label, idx
                        )
                    }
                    names.append(name)
        return names

    def get_parents(self, obj: GeographicalEntity):
        parents = []
        max_level = self.context['max_level']
        related = ''
        for i in range(max_level):
            related = related + (
                '__parent' if i > 0 else 'parent'
            )
            parent_code = obj.get(f'{related}__internal_code', '')
            unique_code = obj.get(f'{related}__unique_code', '')
            unique_code_version = obj.get(
                f'{related}__unique_code_version',
                1
            )
            admin_level = obj.get(f'{related}__level', '')
            type = obj.get(f'{related}__type__label', '')
            if parent_code and unique_code:
                parents.append({
                    'default': parent_code,
                    'ucode': get_unique_code(
                        unique_code,
                        unique_code_version
                    ),
                    'admin_level': admin_level,
                    'type': type
                })
            elif self.output_format == 'geojson':
                parents.append({
                    'default': None,
                    'ucode': None,
                    'admin_level': i,
                    'type': None
                })
        return parents

    def to_representation(self, instance: GeographicalEntity):
        representation = (
            super(GeographicalEntitySerializer, self).
            to_representation(instance)
        )
        if self.output_format == 'simple':
            return representation
        results = []
        for k, v in representation.items():
            if k == 'properties':
                if 'ext_codes' in v:
                    for code, value in v['ext_codes'].items():
                        v[code] = value
                    del v['ext_codes']
                if 'names' in v:
                    for value in v['names']:
                        label = (
                            value['label'] if value and 'label' in value else
                            None
                        )
                        if label:
                            v[label] = (
                                value['name'] if value and 'name' in value else
                                None
                            )
                    del v['names']
                if 'parents' in v:
                    for parent in v['parents']:
                        parent_key = f"adm{parent['admin_level']}"
                        for code, value in parent.items():
                            if code == 'admin_level' or code == 'default':
                                continue
                            v[f'{parent_key}_{code}'] = value
                    # remove
                    del v['parents']
            results.append((k, v))
        return OrderedDict(results)

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'Geographical Entity Detail',
            'properties': {
                'name': openapi.Schema(
                    title='Geographical entity name',
                    type=openapi.TYPE_STRING
                ),
                'ucode': openapi.Schema(
                    title='Unicef code',
                    type=openapi.TYPE_STRING,
                ),
                'concept_ucode': openapi.Schema(
                    title='Unicef concept ucode',
                    type=openapi.TYPE_STRING,
                ),
                'uuid': openapi.Schema(
                    title='UUID revision',
                    type=openapi.TYPE_STRING,
                ),
                'concept_uuid': openapi.Schema(
                    title='UUID that persist between revision',
                    type=openapi.TYPE_STRING,
                ),
                'admin_level': openapi.Schema(
                    title='Admin level of geographical entity',
                    type=openapi.TYPE_INTEGER,
                ),
                'level_name': openapi.Schema(
                    title='Admin level name',
                    type=openapi.TYPE_STRING,
                ),
                'type': openapi.Schema(
                    title='Name of entity type',
                    type=openapi.TYPE_STRING,
                ),
                'start_date': openapi.Schema(
                    title='Start date of this geographical entity revision',
                    type=openapi.TYPE_STRING,
                ),
                'end_date': openapi.Schema(
                    title='End date of this geographical entity revision',
                    type=openapi.TYPE_STRING,
                ),
                'ext_codes': openapi.Schema(
                    title='Other external codes',
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'default': openapi.Schema(
                            title='Default code',
                            type=openapi.TYPE_STRING,
                        ),
                        '<IdExtCode>': openapi.Schema(
                            title='Other external code',
                            type=openapi.TYPE_STRING,
                        )
                    }
                ),
                'names': openapi.Schema(
                    title='Other names',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'name': openapi.Schema(
                                title='Name',
                                type=openapi.TYPE_STRING
                            ),
                            'lang': openapi.Schema(
                                title='ISO 639-1 language code',
                                type=openapi.TYPE_STRING
                            ),
                            'label': openapi.Schema(
                                title='Label of the name',
                                type=openapi.TYPE_STRING
                            )
                        }
                    )
                ),
                'is_latest': openapi.Schema(
                    title='True if this is latest revision',
                    type=openapi.TYPE_BOOLEAN,
                ),
                'bbox': openapi.Schema(
                    title='Bounding box of this geographical entity',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_NUMBER
                    )
                ),
                'parents': openapi.Schema(
                    title='All parents in upper level',
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'admin_level': openapi.Schema(
                                title='Admin level of parent',
                                type=openapi.TYPE_INTEGER,
                            ),
                            'type': openapi.Schema(
                                title='Name of parent admin level',
                                type=openapi.TYPE_STRING,
                            ),
                            'default': openapi.Schema(
                                title='Default code of parent',
                                type=openapi.TYPE_STRING,
                            ),
                            'ucode': openapi.Schema(
                                title='Unicef code of parent',
                                type=openapi.TYPE_STRING,
                            )
                        }
                    )
                ),
                'centroid': openapi.Schema(
                    title='Centroid is returned if geom=centroid',
                    type=openapi.TYPE_STRING,
                ),
                'geometry': openapi.Schema(
                    title='Geometry is returned if geom=full_geom',
                    type=openapi.TYPE_STRING,
                )
            },
            'example': {
                'ucode': 'SY_0001_0007_V1',
                'concept_ucode': '#SY_1',
                'uuid': '89a0e4a0-b327-4f0e-98bd-e97de8d739e6',
                'concept_uuid': '0b3cee0b-477b-40d7-9aa1-48c33689c624',
                'is_latest': True,
                'start_date': '2023-01-09T03:06:27.161475Z',
                'end_date': '',
                'name': 'Jebel Saman',
                'admin_level': 2,
                'level_name': 'District',
                'type': 'District',
                'ext_codes': {
                    'PCode': 'SY0200',
                    'Id': '38675',
                    'default': 'SY0200'
                },
                'names': [
                    {
                        'name': 'Jebel Saman',
                        'lang': 'EN',
                        'label': 'AltName'
                    }
                ],
                'parents': [
                    {
                        'default': 'SY02',
                        'ucode': 'SY_0001',
                        'admin_level': 1,
                        'type': 'Province'
                    },
                    {
                        'default': 'SY',
                        'ucode': 'SY',
                        'admin_level': 0,
                        'type': 'Country'
                    }
                ],
                'bbox': [-121.5, 47.25, -120.4, 47.8],
                'centroid': 'POINT (37.11368735239726 35.99933852889995)'
            }
        }

        model = GeographicalEntity
        fields = [
            'ucode',
            'concept_ucode',
            'uuid',
            'concept_uuid',
            'is_latest',
            'start_date',
            'end_date',
            'name',
            'admin_level',
            'level_name',
            'type',
            'ext_codes',
            'names',
            'parents',
            'bbox',
            'centroid',
            'geometry'
        ]


class GeographicalGeojsonSerializer(
        GeographicalEntitySerializer,
        GeoFeatureModelSerializer):
    output_format = 'geojson'

    class Meta:
        model = GeographicalEntity
        geo_field = 'geometry'
        fields = [
            'ucode',
            'concept_ucode',
            'uuid',
            'concept_uuid',
            'is_latest',
            'start_date',
            'end_date',
            'name',
            'admin_level',
            'level_name',
            'type',
            'ext_codes',
            'names',
            'parents'
        ]


class SimpleGeographicalGeojsonSerializer(
        GeographicalEntitySerializer,
        GeoFeatureModelSerializer):
    output_format = 'geojson'

    class Meta:
        model = GeographicalEntity
        geo_field = 'geometry'
        fields = [
            'id'
        ]


class ExportGeojsonSerializer(
        GeographicalEntitySerializer,
        GeoFeatureModelSerializer):
    remove_empty_fields = False
    output_format = 'geojson'

    def get_geometry(self, obj: GeographicalEntity):
        return None

    def get_concept_uuid(self, obj: GeographicalEntity):
        return str(obj.get('uuid', ''))

    def get_uuid(self, obj: GeographicalEntity):
        return str(obj.get('uuid_revision', ''))

    class Meta:
        model = GeographicalEntity
        geo_field = 'geometry'
        fields = [
            'ucode',
            'uuid',
            'concept_uuid',
            'is_latest',
            'start_date',
            'end_date',
            'name',
            'level',
            'level_name',
            'type',
            'ext_codes',
            'names',
            'parents'
        ]


class ExportShapefileSerializer(
        GeographicalEntitySerializer,
        GeoFeatureModelSerializer):
    cnpt_uuid = serializers.SerializerMethodField()
    remove_empty_fields = False
    output_format = 'geojson'

    def get_geometry(self, obj: GeographicalEntity):
        return None

    def get_cnpt_uuid(self, obj: GeographicalEntity):
        return str(obj.get('uuid', ''))

    def get_uuid(self, obj: GeographicalEntity):
        return str(obj.get('uuid_revision', ''))

    class Meta:
        model = GeographicalEntity
        geo_field = 'geometry'
        fields = [
            'ucode',
            'uuid',
            'cnpt_uuid',
            'is_latest',
            'start_date',
            'end_date',
            'name',
            'level',
            'level_name',
            'type',
            'ext_codes',
            'names',
            'parents'
        ]


class ExportCentroidGeojsonSerializer(
        GeographicalEntitySerializer,
        GeoFeatureModelSerializer):
    remove_empty_fields = False
    output_format = 'geojson'
    c = serializers.SerializerMethodField()
    u = serializers.SerializerMethodField()
    n = serializers.SerializerMethodField()
    b = serializers.SerializerMethodField()
    pc = serializers.SerializerMethodField()
    pu = serializers.SerializerMethodField()

    def get_geometry(self, obj: GeographicalEntity):
        return None

    def get_c(self, obj: GeographicalEntity):
        return str(obj.get('uuid', ''))

    def get_u(self, obj: GeographicalEntity):
        return self.get_ucode(obj)

    def get_n(self, obj: GeographicalEntity):
        return self.get_name(obj)

    def get_b(self, obj: GeographicalEntity):
        if obj['bbox']:
            bbox = ast.literal_eval(obj['bbox'])
            return [round(b, 5) for b in bbox]
        return None

    def get_pc(self, obj: GeographicalEntity):
        pc = []
        level = obj['level']
        related = ''
        for i in range(level):
            related = related + (
                '__parent' if i > 0 else 'parent'
            )
            parent_uuid = obj.get(f'{related}__uuid', '')
            if parent_uuid:
                pc.insert(0, str(parent_uuid))
        return pc

    def get_pu(self, obj: GeographicalEntity):
        pu = []
        level = obj['level']
        related = ''
        for i in range(level):
            related = related + (
                '__parent' if i > 0 else 'parent'
            )
            unique_code = obj.get(f'{related}__unique_code', '')
            unique_code_version = obj.get(
                f'{related}__unique_code_version',
                1
            )
            if unique_code:
                ucode = get_unique_code(unique_code, unique_code_version)
                pu.insert(0, ucode)
        return pu

    class Meta:
        model = GeographicalEntity
        geo_field = 'geometry'
        fields = [
            'c',
            'n',
            'u',
            'b',
            'pc',
            'pu'
        ]


class SearchEntitySerializer(GeographicalEntitySerializer):
    similarity = serializers.SerializerMethodField()

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'Geographical Entity Detail',
            'properties': {
                **GeographicalEntitySerializer.Meta.
                swagger_schema_fields['properties'],
                'similarity': openapi.Schema(
                                title='Name Similarity',
                                description=(
                                    'Value is between 0-1. '
                                    'Higher value is more similar'
                                ),
                                type=openapi.TYPE_NUMBER,
                            )
            },
            'example': {
                **GeographicalEntitySerializer.Meta.
                swagger_schema_fields['example'],
                'similarity': 1.0
            }
        }

        model = GeographicalEntity
        fields = [
            'ucode',
            'concept_ucode',
            'uuid',
            'concept_uuid',
            'is_latest',
            'start_date',
            'end_date',
            'name',
            'admin_level',
            'level_name',
            'type',
            'ext_codes',
            'names',
            'parents',
            'centroid',
            'geometry',
            'similarity',
            'bbox'
        ]

    def get_similarity(self, obj):
        return obj.get('similarity', 0)


class FuzzySearchEntitySerializer(GeographicalEntitySerializer):
    similarity = serializers.SerializerMethodField()
    matching_name = serializers.SerializerMethodField()

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'Geographical Entity Detail',
            'properties': {
                **GeographicalEntitySerializer.Meta.
                swagger_schema_fields['properties'],
                'similarity': openapi.Schema(
                                title='Name Similarity',
                                description=(
                                    'Value is between 0-1. '
                                    'Higher value means more similar'
                                ),
                                type=openapi.TYPE_NUMBER,
                            ),
                'matching_name': openapi.Schema(
                    title='Name of entity from the search result',
                    description=(
                        'Name of entity from the search result'
                    ),
                    type=openapi.TYPE_NUMBER,
                )
            },
            'example': {
                **GeographicalEntitySerializer.Meta.
                swagger_schema_fields['example'],
                'similarity': 1.0,
                'matching_name': 'Malema'
            }
        }

        model = GeographicalEntity
        fields = [
            'ucode',
            'concept_ucode',
            'uuid',
            'concept_uuid',
            'is_latest',
            'start_date',
            'end_date',
            'name',
            'admin_level',
            'level_name',
            'type',
            'ext_codes',
            'names',
            'parents',
            'centroid',
            'geometry',
            'similarity',
            'matching_name',
            'bbox'
        ]

    def get_similarity(self, obj):
        return obj.get('similarity', 0)

    def get_matching_name(self, obj):
        return obj.get('matching_name', '')

    def get_parents(self, obj: GeographicalEntity):
        parents = []
        max_level = self.context['max_level']
        for i in range(max_level):
            field_key = f"parent_{i}"
            parent_code = obj.get(f'{field_key}__internal_code', '')
            unique_code = obj.get(f'{field_key}__unique_code', '')
            unique_code_version = obj.get(
                f'{field_key}__unique_code_version',
                1
            )
            admin_level = obj.get(f'{field_key}__level', '')
            type = obj.get(f'{field_key}__type__label', '')
            if parent_code and unique_code:
                parents.append({
                    'default': parent_code,
                    'ucode': get_unique_code(
                        unique_code,
                        unique_code_version
                    ),
                    'admin_level': admin_level,
                    'type': type
                })
        return parents


class SearchGeometrySerializer(GeographicalEntitySerializer):
    distance = serializers.SerializerMethodField()

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'Geographical Entity Detail',
            'properties': {
                **GeographicalEntitySerializer.Meta.
                swagger_schema_fields['properties'],
                'distance': openapi.Schema(
                                title='Geometry Distance',
                                description='Lower value is more similar',
                                type=openapi.TYPE_NUMBER,
                            )
            },
            'example': {
                **GeographicalEntitySerializer.Meta.
                swagger_schema_fields['example'],
                'distance': 5.313808528450528
            }
        }

        model = GeographicalEntity
        fields = [
            'ucode',
            'concept_ucode',
            'uuid',
            'concept_uuid',
            'is_latest',
            'start_date',
            'end_date',
            'name',
            'admin_level',
            'level_name',
            'type',
            'ext_codes',
            'names',
            'parents',
            'centroid',
            'geometry',
            'distance',
            'bbox'
        ]

    def get_distance(self, obj):
        uuid = self.get_uuid(obj)
        if 'entities_raw' in self.context:
            entities_raw = self.context['entities_raw']
            entity_raw = (
                [entity for entity in entities_raw if
                    getattr(entity, 'uuid_revision', None) == uuid]
            )
            if entity_raw:
                return getattr(entity_raw[0], 'similarity', None)
        return None


class FindEntityByUCodeSerializer(GeographicalEntitySerializer):
    views = serializers.SerializerMethodField()

    class Meta:
        swagger_schema_fields = {
            'type': openapi.TYPE_OBJECT,
            'title': 'Entity Detail by UCode/CUCode',
            'properties': {
                **GeographicalEntitySerializer.Meta.
                swagger_schema_fields['properties'],
                'views': openapi.Schema(
                                title='Views that entity belongs to',
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Items(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'name': openapi.Schema(
                                            title='View name',
                                            type=openapi.TYPE_STRING
                                        ),
                                        'uuid': openapi.Schema(
                                            title='View UUID',
                                            type=openapi.TYPE_STRING
                                        )
                                    }
                                )
                            )
            },
            'example': {
                **GeographicalEntitySerializer.Meta.
                swagger_schema_fields['example'],
                'views': [
                    {
                        'name': 'World Boundaries (Latest)',
                        'uuid': '7b3849ee-7a5b-40e0-8d47-d0eeb2434a42'
                    }
                ]
            }
        }

        model = GeographicalEntity
        fields = [
            'ucode',
            'concept_ucode',
            'uuid',
            'concept_uuid',
            'is_latest',
            'start_date',
            'end_date',
            'name',
            'admin_level',
            'level_name',
            'type',
            'ext_codes',
            'names',
            'parents',
            'centroid',
            'geometry',
            'bbox',
            'views'
        ]

    def get_views(self, obj):
        views = self.context.get('view_list', [])
        result = []
        for view in views:
            result.append({
                'name': view.name,
                'uuid': str(view.uuid)
            })
        return result


class FindEntityByUcodeGeojsonSerializer(
        GeographicalEntitySerializer,
        GeoFeatureModelSerializer):
    output_format = 'geojson'
    views = serializers.SerializerMethodField()

    class Meta:
        model = GeographicalEntity
        geo_field = 'geometry'
        fields = [
            'ucode',
            'concept_ucode',
            'uuid',
            'concept_uuid',
            'is_latest',
            'start_date',
            'end_date',
            'name',
            'admin_level',
            'level_name',
            'type',
            'ext_codes',
            'names',
            'parents'
        ]

    def get_views(self, obj):
        views = self.context.get('view_list', [])
        result = []
        for view in views:
            result.append(view.name)
        return ','.join(result)

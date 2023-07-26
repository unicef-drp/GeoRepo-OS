import json
import math
import uuid
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchVector
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from area import area

from azure_auth.backends import AzureAuthRequiredMixin
from dashboard.models import EntityUploadStatus, BoundaryComparison
from georepo.models import GeographicalEntity, BoundaryType
from modules.admin_boundaries.admin_boundary_matching import (
    get_closest_entities,
    compare_entities,
    recalculate_summary,
    check_is_same_entity
)
from georepo.utils.unique_code import (
    get_version_code,
    count_max_unique_code,
    generate_unique_code_base
)

BUFFER_EXTENT = 0.5


class BoundaryComparisonSummary(AzureAuthRequiredMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=kwargs.get('entity_upload_id')
        )
        if not entity_upload.boundary_comparison_summary:
            if not entity_upload.comparison_running:
                # Trigger comparison process
                pass
            return Response(None)
        return Response(
            entity_upload.boundary_comparison_summary
        )


class BoundaryComparisonSerializer(serializers.ModelSerializer):
    same_entity = serializers.SerializerMethodField()
    new_name = serializers.SerializerMethodField()
    default_new_code = serializers.SerializerMethodField()
    matching_name = serializers.SerializerMethodField()
    new_code = serializers.SerializerMethodField()
    matching_code = serializers.SerializerMethodField()
    matching_version = serializers.SerializerMethodField()
    matching_level = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    parent_code = serializers.SerializerMethodField()
    geometry_similarity_new = serializers.SerializerMethodField()
    geometry_similarity_matching = serializers.SerializerMethodField()
    name_similarity = serializers.SerializerMethodField()
    code_match = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    new_area = serializers.SerializerMethodField()
    old_area = serializers.SerializerMethodField()
    new_perimeter = serializers.SerializerMethodField()
    old_perimeter = serializers.SerializerMethodField()
    default_old_code = serializers.SerializerMethodField()
    old_parent_name = serializers.SerializerMethodField()
    old_parent_code = serializers.SerializerMethodField()
    ucode_version = serializers.SerializerMethodField()

    def get_same_entity(self, obj: BoundaryComparison):
        return 'Yes' if obj.is_same_entity else 'No'

    def get_distance(self, obj: BoundaryComparison):
        return obj.centroid_distance if obj.centroid_distance else 0

    def get_code_match(self, obj: BoundaryComparison):
        if obj.code_match is not None:
            return 'Yes' if obj.code_match else 'No'
        return ''

    def get_name_similarity(self, obj: BoundaryComparison):
        return (
            round(obj.name_similarity * 100, 3)
            if obj.name_similarity else 0
        )

    def get_new_name(self, obj: BoundaryComparison):
        return obj.main_boundary.label if obj.main_boundary else ''

    def get_default_new_code(self, obj: BoundaryComparison):
        return obj.main_boundary.internal_code if obj.main_boundary else ''

    def get_matching_name(self, obj: BoundaryComparison):
        return obj.comparison_boundary.label if obj.comparison_boundary else ''

    def get_new_code(self, obj: BoundaryComparison):
        return obj.main_boundary.unique_code if obj.main_boundary else ''

    def get_matching_code(self, obj: BoundaryComparison):
        return (
            obj.comparison_boundary.unique_code if obj.comparison_boundary
            else ''
        )

    def get_matching_version(self, obj: BoundaryComparison):
        return (
            get_version_code(obj.comparison_boundary.unique_code_version) if
            obj.comparison_boundary else ''
        )

    def get_matching_level(self, obj: BoundaryComparison):
        return (
            str(obj.comparison_boundary.level) if
            obj.comparison_boundary else ''
        )

    def get_geometry_similarity_new(self, obj: BoundaryComparison):
        return (
            round(100 * obj.geometry_overlap_new, 2)
            if obj.geometry_overlap_new
            else 0
        )

    def get_geometry_similarity_matching(self, obj: BoundaryComparison):
        return (
            round(100 * obj.geometry_overlap_old, 2)
            if obj.geometry_overlap_old
            else 0
        )

    def get_parent_name(self, obj: BoundaryComparison):
        return obj.main_boundary.parent.label if\
            obj.main_boundary.parent else ''

    def get_parent_code(self, obj: BoundaryComparison):
        return obj.main_boundary.parent.unique_code if\
            obj.main_boundary.parent else ''

    def get_new_area(self, obj: BoundaryComparison):
        if obj.main_boundary and obj.main_boundary.area:
            return round(obj.main_boundary.area, 2)
        return 0

    def get_old_area(self, obj: BoundaryComparison):
        if obj.comparison_boundary and obj.comparison_boundary.area:
            return round(obj.comparison_boundary.area, 2)
        return 0

    def get_new_perimeter(self, obj: BoundaryComparison):
        if obj.main_boundary and obj.main_boundary.geometry:
            return round(
                obj.main_boundary.geometry.length,
                2
            )
        return 0

    def get_old_perimeter(self, obj: BoundaryComparison):
        if obj.comparison_boundary and obj.comparison_boundary.geometry:
            return round(
                obj.comparison_boundary.geometry.length,
                2
            )
        return 0

    def get_default_old_code(self, obj: BoundaryComparison):
        if obj.comparison_boundary:
            return obj.comparison_boundary.internal_code
        return ''

    def get_old_parent_name(self, obj: BoundaryComparison):
        if obj.comparison_boundary and obj.comparison_boundary.parent:
            return obj.comparison_boundary.parent.label
        return ''

    def get_old_parent_code(self, obj: BoundaryComparison):
        if obj.comparison_boundary and obj.comparison_boundary.parent:
            return obj.comparison_boundary.parent.unique_code
        return ''

    def get_ucode_version(self, obj: BoundaryComparison):
        if obj.main_boundary:
            return obj.main_boundary.unique_code_version
        return ''

    class Meta:
        model = BoundaryComparison
        fields = [
            'id', 'same_entity',
            'new_name', 'default_new_code', 'matching_name',
            'new_code', 'matching_code',
            'matching_version', 'matching_level',
            'parent_name', 'parent_code',
            'geometry_similarity_new',
            'geometry_similarity_matching',
            'distance',
            'name_similarity',
            'code_match',
            'is_parent_rematched',
            'new_area', 'old_area',
            'new_perimeter', 'old_perimeter',
            'default_old_code', 'old_parent_name',
            'old_parent_code', 'ucode_version'
        ]

    @staticmethod
    def get_sort_attribute(sort_by=None, direction=None):
        result = None
        if sort_by is None or sort_by == '':
            return 'main_boundary__label'
        if sort_by not in BoundaryComparisonSerializer.Meta.fields:
            return result
        result = sort_by
        # custom field
        custom_fields = {
            'same_entity': 'is_same_entity',
            'new_name': 'main_boundary__label',
            'matching_name': 'comparison_boundary__label',
            'new_code': 'main_boundary__unique_code',
            'matching_code': 'comparison_boundary__unique_code',
            'parent_name': 'main_boundary__parent__label',
            'parent_code': 'main_boundary__parent__unique_code',
            'geometry_similarity_new': 'geometry_overlap_new',
            'geometry_similarity_matching': 'geometry_overlap_old',
            'distance': 'centroid_distance',
            'matching_version': 'comparison_boundary__unique_code_version',
            'matching_level': 'comparison_boundary__level'
        }
        if sort_by in custom_fields:
            result = custom_fields[sort_by]
        # add sort direction
        if direction == 'desc':
            result = f'-{result}'
        return result

    @staticmethod
    def get_search_vector():
        return SearchVector(
            'main_boundary__label',
            'comparison_boundary__label',
            'main_boundary__unique_code',
            'comparison_boundary__unique_code',
            'main_boundary__parent__label',
            'main_boundary__parent__unique_code'
        )


class BoundaryComparisonMatchTable(AzureAuthRequiredMixin, APIView):
    permission_classes = [IsAuthenticated]

    def apply_filter(self, boundary_comparisons):
        search_text = self.request.GET.get('search_text', None)
        if search_text:
            boundary_comparisons = boundary_comparisons.annotate(
                search=BoundaryComparisonSerializer.get_search_vector()
            ).filter(search__icontains=search_text)
        boolean_filters = {
            'same_entity': 'is_same_entity',
            'code_match': 'code_match',
            'is_parent_rematched': 'is_parent_rematched'
        }
        for req_key, field in boolean_filters.items():
            req_filter = self.request.GET.get(req_key, None)
            if req_filter:
                filter_by_boolean = {
                    field: req_filter.lower() == 'yes'
                }
                boundary_comparisons = boundary_comparisons.filter(
                    **filter_by_boolean
                )
        value_range_filters = {
            'geometry_similarity_new': 'geometry_overlap_new',
            'geometry_similarity_matching': 'geometry_overlap_old',
            'distance': 'centroid_distance',
            'name_similarity': 'name_similarity'
        }
        for req_key, field in value_range_filters.items():
            req_filter_min = self.request.GET.get(
                f'min_{req_key}',
                None
            )
            req_filter_max = self.request.GET.get(
                f'max_{req_key}',
                None
            )
            if req_filter_min is not None and req_filter_max is not None:
                if field == 'centroid_distance':
                    filter_by_range = {
                        f'{field}__range': (
                            float(req_filter_min),
                            float(req_filter_max)
                        )
                    }
                else:
                    filter_by_range = {
                        f'{field}__range': (
                            float(req_filter_min) / 100,
                            float(req_filter_max) / 100
                        )
                    }
                boundary_comparisons = boundary_comparisons.filter(
                    **filter_by_range
                )
        return boundary_comparisons

    def get(self, *args, **kwargs):
        level = int(kwargs.get('level', '0'))
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=kwargs.get('entity_upload_id')
        )
        page = int(self.request.GET.get('page', '1'))
        page_size = int(self.request.GET.get('page_size', '50'))
        sort_by = self.request.GET.get('sort_by', None)
        sort_direction = self.request.GET.get('sort_direction', None)
        sort_criteria = BoundaryComparisonSerializer.get_sort_attribute(
            sort_by,
            sort_direction
        )
        parent_id_key = 'id'
        for i in range(level):
            parent_id_key = 'parent__' + parent_id_key
        main_boundaries = GeographicalEntity.objects.filter(
            level=level,
            **{parent_id_key: entity_upload.revised_geographical_entity.id}
        )
        boundary_comparisons = BoundaryComparison.objects.filter(
            main_boundary__in=main_boundaries
        ).select_related('main_boundary__parent')
        boundary_comparisons = self.apply_filter(boundary_comparisons)
        if sort_criteria:
            boundary_comparisons = boundary_comparisons.order_by(sort_criteria)
        paginator = Paginator(boundary_comparisons, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = (
                BoundaryComparisonSerializer(
                    paginated_entities, many=True).data
            )
        return Response(status=200, data={
            'count': paginator.count,
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output
        })


class BoundaryComparisonGeometry(AzureAuthRequiredMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        boundary_comparison = get_object_or_404(
            BoundaryComparison,
            id=kwargs.get('boundary_comparison_id')
        )
        response_data = {}
        bbox = []
        if boundary_comparison.main_boundary:
            response_data['main_boundary_geom'] = (
                json.loads(
                    boundary_comparison.main_boundary.geometry.geojson
                )
            )
            area_km = boundary_comparison.main_boundary.area
            if not area_km:
                area_km = area(
                        boundary_comparison.main_boundary.
                        geometry.geojson,
                ) / 1e+6
                boundary_comparison.main_boundary.area = area_km
                boundary_comparison.main_boundary.save()

            response_data['main_boundary_data'] = {
                'label': boundary_comparison.main_boundary.label,
                'code': boundary_comparison.main_boundary.ucode,
                'area': (
                    round(
                        area_km,
                        2)
                ),
                'perimeter': (
                    round(
                        boundary_comparison.main_boundary.geometry.
                        length,
                        2
                    )
                )
            }

            bbox = (
                boundary_comparison.main_boundary.geometry.extent
            )
        if boundary_comparison.comparison_boundary:
            response_data['comparison_boundary_geom'] = (
                json.loads(
                    boundary_comparison.comparison_boundary.geometry.geojson
                )
            )
            area_km = boundary_comparison.comparison_boundary.area
            union = (
                boundary_comparison.main_boundary.geometry.union(
                    boundary_comparison.comparison_boundary.geometry
                )
            )
            if union:
                bbox = union.extent
            if not area_km:
                area_km = area(
                    boundary_comparison.comparison_boundary.
                    geometry.geojson,
                ) / 1e+6
                boundary_comparison.comparison_boundary.area = area_km
                boundary_comparison.comparison_boundary.save()
            response_data['comparison_boundary_data'] = {
                'label': boundary_comparison.comparison_boundary.label,
                'code': boundary_comparison.comparison_boundary.ucode,
                'area': (
                    round(
                        area_km,
                        2)
                ),
                'perimeter': (
                    round(
                        boundary_comparison.comparison_boundary.geometry.
                        length,
                        2
                    )
                )
            }

        response_data['bbox'] = bbox
        return Response(response_data)


class BoundaryLineSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    def get_code(self, obj: GeographicalEntity):
        return obj.ucode

    def get_type(self, obj: GeographicalEntity):
        boundary_type = BoundaryType.objects.filter(
            type=obj.type,
            dataset=obj.dataset
        ).first()
        return boundary_type.value

    class Meta:
        model = GeographicalEntity
        fields = ['id', 'code', 'type']

    @staticmethod
    def get_sort_attribute(sort_by=None, direction=None):
        result = None
        if sort_by not in BoundaryLineSerializer.Meta.fields:
            return result
        result = sort_by
        # custom field
        custom_fields = {
            'code': 'unique_code'
        }
        if sort_by in custom_fields:
            result = custom_fields[sort_by]
        # add sort direction
        if direction == 'desc':
            result = f'-{result}'
        return result

    @staticmethod
    def get_search_vector():
        return SearchVector(
            'unique_code',
            'unique_code_version'
        )


class BoundaryLinesMatchTable(AzureAuthRequiredMixin, APIView):
    permission_classes = [IsAuthenticated]

    def apply_filter(self, entities):
        search_text = self.request.GET.get('search_text', None)
        if search_text:
            entities = entities.annotate(
                search=BoundaryLineSerializer.get_search_vector()
            ).filter(search__icontains=search_text)
        return entities

    def get(self, *args, **kwargs):
        type = kwargs.get('type', '')
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=kwargs.get('entity_upload_id')
        )
        page = int(self.request.GET.get('page', '1'))
        page_size = int(self.request.GET.get('page_size', '50'))
        sort_by = self.request.GET.get('sort_by', None)
        sort_direction = self.request.GET.get('sort_direction', None)
        sort_criteria = BoundaryLineSerializer.get_sort_attribute(
            sort_by,
            sort_direction
        )
        if type == '':
            return Response([])
        entities = GeographicalEntity.objects.filter(
            dataset=entity_upload.upload_session.dataset,
            revision_number=entity_upload.revision_number
        ).order_by('id')
        entities = self.apply_filter(entities)
        if sort_criteria:
            entities = entities.order_by(sort_criteria)
        paginator = Paginator(entities, page_size)
        total_page = math.ceil(paginator.count / page_size)
        if page > total_page:
            output = []
        else:
            paginated_entities = paginator.get_page(page)
            output = (
                BoundaryLineSerializer(
                    paginated_entities, many=True).data
            )
        return Response(status=200, data={
            'count': paginator.count,
            'page': page,
            'total_page': total_page,
            'page_size': page_size,
            'results': output
        })


class BoundaryLinesGeometry(AzureAuthRequiredMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        entity = get_object_or_404(
            GeographicalEntity,
            id=kwargs.get('id')
        )
        response_data = {
            'geom': json.loads(entity.geometry.geojson),
            'bbox': entity.geometry.extent
        }
        return Response(response_data)


class ClosestEntitySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()
    version = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    geometry_similarity_new = serializers.SerializerMethodField()
    geometry_similarity_match = serializers.SerializerMethodField()

    def get_name(self, obj: GeographicalEntity):
        return obj.label

    def get_type(self, obj: GeographicalEntity):
        return obj.type.label

    def get_code(self, obj: GeographicalEntity):
        return obj.unique_code

    def get_version(self, obj: GeographicalEntity):
        return get_version_code(obj.unique_code_version)

    def get_level(self, obj: GeographicalEntity):
        return obj.level

    def get_geometry_similarity_new(self, obj: GeographicalEntity):
        if hasattr(obj, 'overlap_new'):
            return round(100 * obj.overlap_new, 2)
        return ''

    def get_geometry_similarity_match(self, obj: GeographicalEntity):
        if hasattr(obj, 'overlap_old'):
            return round(100 * obj.overlap_old, 2)
        return ''

    class Meta:
        model = GeographicalEntity
        fields = [
            'id',
            'name',
            'type',
            'code',
            'version',
            'level',
            'geometry_similarity_new',
            'geometry_similarity_match'
        ]


class RematchClosestEntities(AzureAuthRequiredMixin, APIView):
    """Retrieve closest entities given target Id"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        boundary_comparison = get_object_or_404(
            BoundaryComparison,
            id=kwargs.get('boundary_comparison_id')
        )
        page = int(request.GET.get('page', '1'))
        page_size = int(request.GET.get('page_size', '5'))
        search_text = request.GET.get('search', '')
        entity = boundary_comparison.main_boundary
        _, closest_entities = get_closest_entities(
            entity, search_text)
        if boundary_comparison.comparison_boundary:
            closest_entities = closest_entities.exclude(
                id=boundary_comparison.comparison_boundary.id
            )
        total_count = closest_entities.count()
        if total_count == 0:
            return Response(status=200, data={
                'count': 0,
                'page': page,
                'total_page': 0,
                'page_size': page_size,
                'results': []
            })
        offset = (page - 1) * page_size
        limit = page_size
        closest_entities = closest_entities[offset:offset + limit]
        return Response(status=200, data={
            'count': total_count,
            'page': page,
            'total_page': math.ceil(total_count / page_size),
            'page_size': page_size,
            'results': (
                ClosestEntitySerializer(closest_entities, many=True).data
            )
        })


class CompareBoundary(AzureAuthRequiredMixin, APIView):
    """Run comparison to target and source entities"""
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=kwargs.get('entity_upload_id')
        )
        ancestor_entity = entity_upload.revised_geographical_entity
        new_entities = (
            ancestor_entity.
            all_children().filter(
                layer_file__in=entity_upload.upload_session
                .layerfile_set.all(),
            ).order_by('level', 'internal_code')
        )
        boundary_comparison = get_object_or_404(
            BoundaryComparison,
            id=kwargs.get('boundary_comparison_id')
        )
        entity_target = boundary_comparison.main_boundary
        entity_source = get_object_or_404(
            GeographicalEntity,
            id=kwargs.get('source_id')
        )
        # validate whether the entity_source is not used in boundary comp
        is_already_used = BoundaryComparison.objects.filter(
            main_boundary__in=new_entities,
            comparison_boundary__uuid=entity_source.uuid
        )
        if is_already_used.exists():
            comparison = is_already_used.first()
            return Response(
                status=400,
                data={
                    'detail': (
                        'The selected entity has been used as comparison '
                        f'for entity {comparison.main_boundary.ucode}'
                    )
                }
            )
        comparison = compare_entities(
            entity_target,
            entity_source
        )
        comparison['geometry_overlap_new'] = (
            round(100 * comparison['geometry_overlap_new'], 4)
        )
        comparison['geometry_overlap_old'] = (
            round(100 * comparison['geometry_overlap_old'], 4)
        )
        return Response(comparison)


def generate_new_unique_code(entity_target):
    max_sequence = count_max_unique_code(
        entity_target.dataset,
        entity_target.level,
        entity_target.parent,
        unique_code_version=entity_target.unique_code_version
    )
    sequence_number = str(max_sequence + 1).zfill(4)
    parent_unique_code = (
        entity_target.parent.unique_code if
        entity_target.parent else
        None
    )
    unique_code = generate_unique_code_base(
        entity_target, parent_unique_code, sequence_number
    )
    entity_target.unique_code = unique_code
    entity_target.save(update_fields=['unique_code'])


def reallocate_new_unique_code(entity_target, unique_code):
    parent_unique_code = (
        entity_target.parent.unique_code if
        entity_target.parent else
        None
    )
    entities = GeographicalEntity.objects.filter(
        dataset=entity_target.dataset,
        level=entity_target.level,
        unique_code_version=entity_target.unique_code_version,
        parent=entity_target.parent
    )
    codes = unique_code.split('_')
    sequence_number = int(codes[-1]) + 1
    prev_unique_code = unique_code
    next_unique_code = generate_unique_code_base(
        entity_target, parent_unique_code, sequence_number
    )
    entity = entities.filter(unique_code=next_unique_code).first()
    while (entity):
        # change entity unique_code
        tmp_unique_code = entity.unique_code
        entity.unique_code = prev_unique_code
        entity.save(update_fields=['unique_code'])
        prev_unique_code = tmp_unique_code
        # increment sequence number
        sequence_number += 1
        next_unique_code = generate_unique_code_base(
            entity_target, parent_unique_code, sequence_number
        )
        entity = entities.filter(unique_code=next_unique_code).first()


class ConfirmRematchBoundary(AzureAuthRequiredMixin, APIView):
    """Replace comparison boundary with selected source entity"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        boundary_comparison = get_object_or_404(
            BoundaryComparison,
            id=kwargs.get('boundary_comparison_id')
        )
        entity_target = boundary_comparison.main_boundary
        entity_source = get_object_or_404(
            GeographicalEntity,
            id=request.data.get('source_id')
        )
        entity_upload = get_object_or_404(
            EntityUploadStatus,
            id=request.data.get('entity_upload_id')
        )
        # compare
        comparison = compare_entities(entity_target, entity_source)
        # update boundary obj
        boundary_comparison.comparison_boundary = entity_source
        boundary_comparison.code_match = comparison['code_match']
        boundary_comparison.name_similarity = comparison['name_similarity']
        boundary_comparison.geometry_overlap_new = (
            comparison['geometry_overlap_new']
        )
        boundary_comparison.geometry_overlap_old = (
            comparison['geometry_overlap_old']
        )
        temp_is_same_entity = boundary_comparison.is_same_entity
        boundary_comparison.is_same_entity = check_is_same_entity(
            entity_target.dataset,
            comparison['geometry_overlap_new'],
            comparison['geometry_overlap_old']
        )
        """
        1 same entity to same entity --> normal, use ucode in target
        2 same entity to new entity --> normal, generate new ucode with max+1
        3 new entity to new entity --> no change in the ucode
        4 new entity to same entity --> allocated new ucode should be
          assigned to next entity?
        """
        if boundary_comparison.is_same_entity:
            # reuse the comparison entity concept_uuid
            entity_target.uuid = entity_source.uuid
            # reuse the unique code
            temp_unique_code = entity_target.unique_code
            entity_target.unique_code = entity_source.unique_code
            entity_target.save(update_fields=['uuid', 'unique_code'])
            if (
                not temp_is_same_entity and entity_target.level > 0 and
                entity_target.parent
            ):
                reallocate_new_unique_code(entity_target, temp_unique_code)
        else:
            # generate new unique code
            if temp_is_same_entity:
                generate_new_unique_code(entity_target)
            entity_target.uuid = uuid.uuid4()
            entity_target.save(update_fields=['uuid'])

        boundary_comparison.save()
        # update summary data
        recalculate_summary(entity_upload)
        return Response(status=204)


class SwapEntityConcept(AzureAuthRequiredMixin, APIView):
    """
    Swap entity concept flag in boundary comparison
    Payload: {
        boundary_comparison_id: 123
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        boundary_comparison = get_object_or_404(
            BoundaryComparison,
            id=request.data.get('boundary_comparison_id')
        )
        if not boundary_comparison.comparison_boundary:
            return Response(
                status=400,
                data={
                    'detail': (
                        'Cannot swap entity without comparison'
                    )
                }
            )
        temp_is_same_entity = boundary_comparison.is_same_entity
        boundary_comparison.is_same_entity = (
            not boundary_comparison.is_same_entity
        )
        entity_target = boundary_comparison.main_boundary
        entity_source = boundary_comparison.comparison_boundary
        if boundary_comparison.is_same_entity:
            # reuse the comparison entity concept_uuid
            entity_target.uuid = entity_source.uuid
            # reuse the unique code
            temp_unique_code = entity_target.unique_code
            entity_target.unique_code = entity_source.unique_code
            entity_target.save(update_fields=['uuid', 'unique_code'])
            if (
                not temp_is_same_entity and entity_target.level > 0 and
                entity_target.parent
            ):
                reallocate_new_unique_code(entity_target, temp_unique_code)
        else:
            # generate new unique code
            if temp_is_same_entity:
                generate_new_unique_code(entity_target)
            entity_target.uuid = uuid.uuid4()
            entity_target.save(update_fields=['uuid'])
        boundary_comparison.save()
        return Response(status=204)

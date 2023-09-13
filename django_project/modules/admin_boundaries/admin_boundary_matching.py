import logging
import time

from typing import Tuple
from difflib import SequenceMatcher
from area import area
from django.contrib.gis.db.models.functions import Intersection, Area
from django.db.models import (
    Avg, F, Q, Case, When,
    FloatField, ExpressionWrapper
)
from django.contrib.gis.measure import D
from django.db.models.query import QuerySet
from dashboard.models import (
    EntityUploadStatus,
    EntityUploadChildLv1,
    LayerUploadSession
)
from dashboard.models.boundary_comparison import BoundaryComparison
from georepo.models import GeographicalEntity, EntityName, Dataset
from georepo.utils.unique_code import (
    generate_upload_unique_code_version,
    get_version_code,
    generate_unique_code_from_comparison,
    generate_unique_code_base,
    count_max_unique_code
)
from modules.admin_boundaries.config import (
    get_new_entities_in_upload
)

logger = logging.getLogger(__name__)

MAX_CLOSEST = 5


class AdminSummaryData(object):
    def __init__(self,
                 level: int,
                 new_count: int,
                 old_count: int,
                 new_total_area: str,
                 old_total_area: str,
                 matching_count: int,
                 avg_similarity_new: float,
                 avg_similarity_old: float):
        self.level = level
        self.new_count = new_count
        self.old_count = old_count
        self.new_total_area = new_total_area
        self.old_total_area = old_total_area
        self.matching_count = matching_count
        self.avg_similarity_new = avg_similarity_new
        self.avg_similarity_old = avg_similarity_old


class AdminBoundaryMatching(object):
    entity_upload = None
    new_entities = None
    log_object = None

    def __init__(self, entity_upload: EntityUploadStatus, **kwargs):
        self.entity_upload = entity_upload
        self.log_object = kwargs.get('log_object')

    def save_progress(self, progress: str):
        self.entity_upload.progress = progress
        self.entity_upload.save(update_fields=['progress'])

    @staticmethod
    def highest_overlap(
            entity_target: QuerySet[GeographicalEntity],
            entity_source: GeographicalEntity) -> Tuple[
                GeographicalEntity | None, float, float]:
        """
        ***DEPRECATED***
        Find the highest overlap of entity_source with data from
         entity_target
        :return: Tuple of the highest overlap entity and percentage of
        the total overlap area %new and %old
        """
        highest_area = 0
        highest_overlap_percentage = (0, 0)
        highest_overlap_entity = None
        for single_entity_target in entity_target:
            intersection_new = entity_source.geometry.intersection(
                single_entity_target.geometry
            )
            overlap_percentage_new = (
                intersection_new.area / single_entity_target.geometry.area
            )
            intersection_old = single_entity_target.geometry.intersection(
                entity_source.geometry
            )
            overlap_percentage_old = (
                intersection_old.area / entity_source.geometry.area
            )
            max_overlap = max(overlap_percentage_new, overlap_percentage_old)
            if max_overlap > highest_area:
                highest_area = max_overlap
                highest_overlap_entity = single_entity_target
                highest_overlap_percentage = (
                    overlap_percentage_new,
                    overlap_percentage_old
                )
        return (
            highest_overlap_entity,
            highest_overlap_percentage[0],
            highest_overlap_percentage[1],
        )

    @staticmethod
    def name_similarity(
            entity_target: GeographicalEntity,
            entity_source: GeographicalEntity) -> float:
        """
        Check name similarity between entity_source and entity_target
        :return: similarity ratio
        """
        entity_target_name = EntityName.objects.filter(
            geographical_entity=entity_target,
            default=True
        )
        if entity_target_name.count() > 0:
            entity_target_name = entity_target_name.first().name
        else:
            entity_target_name = entity_target.label

        entity_source_name = EntityName.objects.filter(
            geographical_entity=entity_source,
            default=True
        )
        if entity_source_name.count() > 0:
            entity_source_name = entity_source_name.first().name
        else:
            entity_source_name = entity_source.label

        return SequenceMatcher(
            None, entity_source_name, entity_target_name
        ).ratio()

    @staticmethod
    def check_code(
            entity_target: GeographicalEntity,
            entity_source: GeographicalEntity) -> bool:
        """
        Check if codes match
        """
        return entity_source.unique_code == entity_target.unique_code

    @staticmethod
    def calculate_centroid_distance(
            entity_target: GeographicalEntity,
            entity_source: GeographicalEntity
    ):
        """
        Calculate centroid distance between two entities
        """
        target_centroid = entity_target.geometry.centroid.transform(
            3857, clone=True
        )
        source_centroid = entity_source.geometry.centroid.transform(
            3857, clone=True
        )
        distance = target_centroid.distance(
            source_centroid
        )
        d = D(m=distance)
        return round(d.km, 2)

    def get_allocated_comparison_entities(self):
        """
        Return concept uuid of entities that has been
        used as comparison boundary
        """
        start = time.time()
        comparisons = BoundaryComparison.objects.filter(
            main_boundary__in=self.new_entities
        ).exclude(
            comparison_boundary__isnull=True
        ).order_by(
            'comparison_boundary__uuid'
        ).distinct(
            'comparison_boundary__uuid'
        ).values_list('comparison_boundary__uuid', flat=True)

        end = time.time()
        if self.log_object:
            self.log_object.add_log('AdminBoundaryMatching.get_allocated_comparison_entities', end - start)

        return comparisons

    def find_comparison_boundary(self,
                                 entity_target: GeographicalEntity) -> Tuple[
            GeographicalEntity | None, float, float]:
        """
        Find comparison boundary using below logic:
        1. check the same admin level in previous revision
        2. if no matching - check the same admin level in all other revisions
        3. if no matching - we check against other admin levels
        in previous revision
        4. if no matching - we check against other admin levels
        in all other revisions

        Comparison boundary should only be matched to 1 new entity

        Return entity if both overlaps are greater than thresholds
        """
        start = time.time()
        
        # get existing comparison entities
        comparisons = self.get_allocated_comparison_entities()
        # check in same admin level
        _, entities = get_closest_entities(
            entity_target,
            search_same_level=True,
            search_prev_version=True,
            above_thresholds_only=True
        )
        entities = entities.exclude(
            uuid__in=comparisons
        )
        if entities.exists():
            entity = entities.first()
            return entity, entity.overlap_new, entity.overlap_old
        # check in same admin level all other revisions
        _, entities = get_closest_entities(
            entity_target,
            search_same_level=True,
            search_prev_version=False,
            above_thresholds_only=True
        )
        entities = entities.exclude(
            uuid__in=comparisons
        )
        if entities.exists():
            entity = entities.first()
            return entity, entity.overlap_new, entity.overlap_old
        # check against other admin level in previous revisions
        _, entities = get_closest_entities(
            entity_target,
            search_same_level=False,
            search_prev_version=True,
            above_thresholds_only=True
        )
        entities = entities.exclude(
            uuid__in=comparisons
        )
        if entities.exists():
            entity = entities.first()
            return entity, entity.overlap_new, entity.overlap_old
        # check against other admin level in all other revisions
        _, entities = get_closest_entities(
            entity_target,
            search_same_level=False,
            search_prev_version=False,
            above_thresholds_only=True
        )
        entities = entities.exclude(
            uuid__in=comparisons
        )
        if entities.exists():
            entity = entities.first()
            return entity, entity.overlap_new, entity.overlap_old
        
        end = time.time()
        if self.log_object:
            self.log_object.add_log('AdminBoundaryMatching.find_comparison_boundary', end - start)
        
        return None, 0, 0

    def find_comparison_boundary_for_non_matching(
            self,
            entity_target: GeographicalEntity) -> Tuple[
                GeographicalEntity | None, float, float]:
        start = time.time()
        
        # get existing comparison entities
        comparisons = self.get_allocated_comparison_entities()
        # for entities without non-matching boundaries, then find
        # from same level and prev version
        # this should be done as last option
        # so that we don't reserve non-matching boundary
        # with entities in top order
        _, entities = get_closest_entities(
            entity_target,
            search_same_level=True,
            search_prev_version=False,
            above_thresholds_only=False
        )
        entities = entities.exclude(
            uuid__in=comparisons
        )
        if entities.exists():
            entity = entities.first()
            return entity, entity.overlap_new, entity.overlap_old
        
        end = time.time()
        if self.log_object:
            self.log_object.add_log('AdminBoundaryMatching.find_comparison_boundary_for_non_matching', end - start)
        
        return None, 0, 0

    def process_comparison_boundary(self,
                                    dataset: Dataset,
                                    main_boundary: GeographicalEntity,
                                    boundary_comparison: BoundaryComparison,
                                    highest_overlap: GeographicalEntity,
                                    overlap_new, overlap_old):
        start = time.time()
        boundary_comparison.comparison_boundary = highest_overlap
        boundary_comparison.geometry_overlap_new = overlap_new
        boundary_comparison.geometry_overlap_old = overlap_old
        if highest_overlap:
            # this will always be true because we filter by
            # overlap thresholdswhen we searching for boundary matching
            boundary_comparison.is_same_entity = check_is_same_entity(
                dataset,
                overlap_new,
                overlap_old
            )
            if boundary_comparison.is_same_entity:
                # reuse the comparison entity concept_uuid
                main_boundary.uuid = highest_overlap.uuid
                main_boundary.save(update_fields=['uuid'])
                # generate unique code base from comparison boundary
                generate_unique_code_from_comparison(main_boundary,
                                                     highest_overlap)

            boundary_comparison.code_match = self.check_code(
                entity_target=main_boundary,
                entity_source=highest_overlap
            )
            boundary_comparison.name_similarity = self.name_similarity(
                entity_target=main_boundary,
                entity_source=highest_overlap
            )
            boundary_comparison.centroid_distance = (
                self.calculate_centroid_distance(
                    entity_target=main_boundary,
                    entity_source=highest_overlap
                )
            )
        else:
            logger.debug('Unable to find matching boundary '
                         f'{main_boundary.internal_code}')
            boundary_comparison.code_match = 0
            boundary_comparison.name_similarity = 0
            boundary_comparison.is_same_entity = False
        # get status parent rematched
        boundary_comparison.is_parent_rematched = (
            EntityUploadChildLv1.objects.filter(
                entity_upload=self.entity_upload,
                entity_id=main_boundary.internal_code,
                is_parent_rematched=True
            ).exists()
        )
        boundary_comparison.save()
        end = time.time()
        if self.log_object:
            self.log_object.add_log('AdminBoundaryMatching.process_comparison_boundary', end - start)

    def check_entities(self):
        """
        Find all overlapping boundaries from the old dataset –
        calculate the percent of overlap
        (% of new boundary overlapping the old one and % of the old one
        overlapping the new one) –
        select the old boundary which has the highest overlap with the old
        boundary as a matching one
        :return:
        """
        start = time.time()
        ancestor_entity = self.entity_upload.revised_geographical_entity
        dataset = ancestor_entity.dataset
        upload_session: LayerUploadSession = self.entity_upload.upload_session
        # ordering of boundary matching is
        # by default code (internal_code/ISO3) in a upload
        # this is to ensure the stability when searching for boundary matching
        self.new_entities = (
            get_new_entities_in_upload(self.entity_upload)
        )

        # generate unique_code_version for entity upload
        revision_start_date = (
            upload_session.started_at if
            not upload_session.is_historical_upload else
            upload_session.historical_start_date
        )
        version = generate_upload_unique_code_version(
            dataset,
            revision_start_date,
            self.entity_upload.original_geographical_entity
        )
        logger.info(f'Generating upload unique_code_version {version}')
        self.entity_upload.unique_code_version = version
        self.entity_upload.save()
        self.new_entities.update(
            unique_code=''
        )
        # check if ancestor is not in new entities
        if (not self.new_entities.filter(
            id=ancestor_entity.id
        ).exists() and not ancestor_entity.unique_code_version):
            logger.info('Generating ancestor entity unique_code_version'
                        f' {self.entity_upload.unique_code_version}')
            ancestor_entity.unique_code_version = (
                self.entity_upload.unique_code_version
            )
            ancestor_entity.save()
        total_entities = self.new_entities.count()
        entity_count = 0
        self.save_progress(f'Processing {entity_count}/{total_entities}')
        logger.info(self.entity_upload.progress)
        entity: GeographicalEntity
        for entity in self.new_entities.iterator(chunk_size=1):
            if not entity.unique_code_version:
                entity.unique_code_version = (
                    self.entity_upload.unique_code_version
                )
                entity.save()

            if entity.level == 0:
                # generate ucode for level 0
                entity.unique_code = generate_unique_code_base(
                    entity, None, None
                )
                entity.save()

            boundary_comparison, _ = BoundaryComparison.objects.get_or_create(
                main_boundary=entity,
            )

            if (
                not entity.geometry
            ):
                continue
            # Update Improvement: only starts searching for revision > 1
            highest_overlap = None
            overlap_new = 0
            overlap_old = 0
            if (
                self.entity_upload.revision_number and
                self.entity_upload.revision_number > 1
            ):
                # Find entities comparison:
                # - WITHIN a given country
                # - ACROSS admin levels
                # - REGARDLESS the unique_code_version
                highest_overlap, overlap_new, overlap_old = (
                    self.find_comparison_boundary(entity)
                )
            self.process_comparison_boundary(
                dataset, entity, boundary_comparison,
                highest_overlap, overlap_new, overlap_old
            )
            entity_count += 1
            if entity_count % 100 == 0:
                self.save_progress(
                    f'Processing {entity_count}/{total_entities}'
                )
            if entity_count % 200 == 0:
                logger.info(f'Processing {entity_count}/{total_entities}')
        self.save_progress(f'Processing {entity_count}/{total_entities}')
        if entity_count % 200 != 0:
            logger.info(self.entity_upload.progress)
        # last iteration to find comparison boundary for
        # entities without matching boundaries above thresholds
        # should use the same order as prev iteration
        comparisons = BoundaryComparison.objects.filter(
            main_boundary__in=self.new_entities,
            comparison_boundary__isnull=True
        ).order_by(
            'main_boundary__level',
            'main_boundary__internal_code'
        )
        entity_count = 0
        total_comparisons = comparisons.count()
        self.save_progress(
            'Processing non-matching boundaries '
            f'{entity_count}/{total_comparisons}'
        )
        logger.info(self.entity_upload.progress)
        for comparison in comparisons.iterator(chunk_size=1):
            # Update Improvement: only starts searching for revision > 1
            highest_overlap = None
            overlap_new = 0
            overlap_old = 0
            if (
                self.entity_upload.revision_number and
                self.entity_upload.revision_number > 1
            ):
                # Find entities comparison for non-matching boundaries:
                # - Within same level
                # - across revisions
                # - regardless above or below thresholds
                highest_overlap, overlap_new, overlap_old = (
                    self.find_comparison_boundary_for_non_matching(
                        comparison.main_boundary
                    )
                )
            self.process_comparison_boundary(
                dataset, comparison.main_boundary, comparison,
                highest_overlap, overlap_new, overlap_old
            )
            entity_count += 1
            if entity_count % 100 == 0:
                self.save_progress(
                    'Processing non-matching boundaries '
                    f'{entity_count}/{total_comparisons}'
                )
            if entity_count % 200 == 0:
                logger.info('Processing non-matching boundaries '
                            f'{entity_count}/{total_comparisons}')
        self.save_progress(
            'Processing non-matching boundaries '
            f'{entity_count}/{total_comparisons}'
        )
        if entity_count % 200 != 0:
            logger.info(self.entity_upload.progress)
        # generate unique code for non-matching boundaries
        self.generate_unique_code_for_new_entities()
        end = time.time()
        if self.log_object:
            self.log_object.add_log('AdminBoundaryMatching.check_entities', end - start)

    def generate_unique_code_for_new_entities(self):
        start = time.time()
        ancestor_entity = self.entity_upload.revised_geographical_entity
        dataset = ancestor_entity.dataset
        total_new_entities_unique_code = self.new_entities.filter(
            unique_code=''
        ).count()
        self.save_progress(
            'Generating new unique code '
            f'for {total_new_entities_unique_code} entities'
        )
        logger.info(self.entity_upload.progress)
        # second iteration to generate new unique code
        # for non matching boundaries,
        # ancestor will have the unique_code generated already
        levels = self.new_entities.filter(
            Q(unique_code='') | Q(unique_code__isnull=True)
        ).order_by('level').distinct('level').values_list('level', flat=True)
        for level in levels:
            if level == 0:
                continue
            new_entities_by_level = self.new_entities.filter(
                level=level
            ).filter(
                Q(unique_code='') | Q(unique_code__isnull=True)
            )
            # ucode generation is for each parent
            parents_by_level = new_entities_by_level.order_by(
                'parent__id'
            ).distinct('parent__id').values_list('parent__id', flat=True)
            for parent_id in parents_by_level:
                parent = GeographicalEntity.objects.get(
                    id=parent_id
                )
                # start of the sequence = max+1
                sequence = count_max_unique_code(dataset, level, parent)
                logger.debug('Generating new unique code '
                             f'for level {level} in '
                             f'parent {parent.unique_code} '
                             f'with starting number: {sequence+1}')
                new_entities_by_level_parent = new_entities_by_level.filter(
                    parent=parent
                ).order_by('internal_code')
                for entity in (
                        new_entities_by_level_parent.iterator(chunk_size=1)):
                    if entity.unique_code:
                        continue
                    unique_code_available = False
                    unique_code = ''
                    while (
                        unique_code_available is False
                    ):
                        sequence += 1
                        sequence_number = str(sequence).zfill(4)
                        parent_unique_code = (
                            entity.parent.unique_code if entity.parent else
                            None
                        )
                        unique_code = generate_unique_code_base(
                            entity, parent_unique_code, sequence_number
                        )
                        unique_code_available = not self.new_entities.filter(
                            level=level,
                            unique_code=unique_code
                        ).exists()
                    if unique_code_available:
                        # success finding vacant unique_code
                        entity.unique_code = unique_code
                        entity.save()
                    else:
                        # failed
                        logger.info('Failed to generate unique code for id '
                                    f'{entity.id}-{entity.label}-'
                                    f'{entity.level}')
        end = time.time()
        if self.log_object:
            self.log_object.add_log('AdminBoundaryMatching.generate_unique_code_for_new_entities', end - start)

    def generate_summary_data(self):
        """
        Generate summary data
        :return: array of AdminSummaryData
        """
        start = time.time()
        summary_data = []
        if not self.new_entities:
            return summary_data
        original_geographical = (
            self.entity_upload.original_geographical_entity
        )
        if not original_geographical:
            original_geographical = (
                self.entity_upload.revised_geographical_entity
            )
        # find prev version
        prev_unique_code_version = None
        prev_entity = GeographicalEntity.objects.filter(
            is_approved=True,
            dataset=self.entity_upload.upload_session.dataset,
            unique_code_version__lt=self.entity_upload.unique_code_version
        ).last()
        if prev_entity:
            prev_unique_code_version = prev_entity.unique_code_version
        levels = self.new_entities.order_by(
            'level').distinct('level').values_list('level', flat=True)
        for level in levels:
            new_entities_by_level = self.new_entities.filter(
                level=level
            )
            boundary_comparisons = BoundaryComparison.objects.filter(
                main_boundary__in=new_entities_by_level,
            )
            old_total_area = 0
            old_entity_count = 0
            if prev_unique_code_version is not None:
                prev_entities = GeographicalEntity.objects.filter(
                    dataset=self.entity_upload.upload_session.dataset,
                    level=level,
                    is_approved=True,
                    unique_code_version=prev_unique_code_version
                )
                old_entity_count = prev_entities.count()
                for prev_entity in prev_entities.iterator(chunk_size=1):
                    if prev_entity.area:
                        old_total_area += prev_entity.area
                    else:
                        old_area = area(
                            prev_entity.geometry.geojson
                        ) / 1e+6 if prev_entity.geometry else 0
                        prev_entity.area = old_area
                        prev_entity.save()
                        old_total_area += old_area

            new_total_area = 0
            if new_entities_by_level:
                for new_entity in (
                        new_entities_by_level.iterator(chunk_size=1)):
                    if new_entity.area:
                        new_total_area += new_entity.area
                    else:
                        new_area = area(
                            new_entity.geometry.geojson
                        ) / 1e+6 if new_entity.geometry else 0
                        new_entity.area = new_area
                        new_entity.save()
                        new_total_area += new_area

            summary_data.append(
                vars(AdminSummaryData(
                    level=level,
                    new_count=new_entities_by_level.count(),
                    old_count=old_entity_count,
                    new_total_area='{} km2'.format(
                        round(new_total_area, 2)
                        if new_total_area else 0
                    ),
                    old_total_area='{} km2'.format(
                        round(old_total_area, 2)
                        if old_total_area else 0
                    ),
                    matching_count=boundary_comparisons.filter(
                        is_same_entity=True
                    ).count(),
                    avg_similarity_new=boundary_comparisons.aggregate(
                        total=Avg(F('geometry_overlap_new')))['total'],
                    avg_similarity_old=boundary_comparisons.aggregate(
                        total=Avg(F('geometry_overlap_old')))['total']
                ))
            )
        end = time.time()
        if self.log_object:
            self.log_object.add_log('AdminBoundaryMatching.generate_summary_data', end - start)
        return summary_data

    def run(self):
        start = time.time()
        self.entity_upload.comparison_data_ready = False
        self.entity_upload.progress = (
            'Boundary Matching - started...'
        )
        self.entity_upload.save()
        logger.info(f'Boundary Matching - {self.entity_upload.id} started...')
        self.check_entities()
        self.save_progress(
            'Boundary Matching - generating summary data...'
        )
        logger.info(
            f'Boundary Matching - {self.entity_upload.id} '
            'generate summary data...'
        )
        summary = self.generate_summary_data()
        logger.info(
            f'Boundary Matching - {self.entity_upload.id} finished...'
        )
        self.entity_upload.progress = (
            'Boundary Matching - finished...'
        )
        self.entity_upload.comparison_data_ready = True
        self.entity_upload.boundary_comparison_summary = (
            summary
        )
        self.entity_upload.save()
        end = time.time()
        if self.log_object:
            self.log_object.add_log('AdminBoundaryMatching.run', end - start)


def check_is_same_entity(
        dataset: Dataset,
        overlap_new: float,
        overlap_old: float) -> bool:
    """
    Is same entity = All Overlaps similarities are above threshold
    """
    threshold_new = (
        dataset.geometry_similarity_threshold_new
    )
    threshold_old = (
        dataset.geometry_similarity_threshold_old
    )
    return (
        overlap_new >= threshold_new and
        overlap_old >= threshold_old
    )


def get_closest_entities(
        entity_target: GeographicalEntity,
        search_text: str = None,
        search_same_level: bool = False,
        search_prev_version: bool = False,
        above_thresholds_only: bool = False,
        **kwargs):
    """
    Find the latest+approved entities that is closest to entity_target
    Return the QuerySet to GeographicalEntity
    """
    start = time.time()
    if not entity_target.geometry:
        return 0, GeographicalEntity.objects.none()
    old_entities = GeographicalEntity.objects.filter(
        is_approved=True,
        dataset=entity_target.dataset
    ).exclude(
        geometry__isnull=True
    )
    if search_same_level:
        old_entities = old_entities.filter(
            level=entity_target.level
        )
    if search_prev_version:
        # find prev version
        prev_entity = GeographicalEntity.objects.filter(
            is_approved=True,
            dataset=entity_target.dataset,
            unique_code_version__lt=entity_target.unique_code_version
        ).order_by('unique_code_version').last()
        if prev_entity:
            old_entities = old_entities.filter(
                unique_code_version=prev_entity.unique_code_version
            )
        else:
            return 0, GeographicalEntity.objects.none()
    # filter by same ancestor
    ancestor_unique_code = (
        entity_target.ancestor.unique_code if
        entity_target.ancestor else
        entity_target.unique_code
    )
    old_entities = old_entities.filter(
        (Q(ancestor__isnull=False) &
         Q(ancestor__unique_code=ancestor_unique_code)) |
        (Q(ancestor__isnull=True) & Q(unique_code=ancestor_unique_code))
    )
    # filter by bbox
    old_entities = old_entities.filter(
        geometry__bboverlaps=entity_target.geometry
    )
    if search_text:
        old_entities = old_entities.filter(
            Q(label__icontains=search_text) |
            Q(internal_code__icontains=search_text) |
            Q(type__label__icontains=search_text) |
            Q(unique_code__icontains=search_text)
        )
    threshold_new = (
        entity_target.dataset.geometry_similarity_threshold_new
    )
    threshold_old = (
        entity_target.dataset.geometry_similarity_threshold_old
    )
    old_entities = old_entities.annotate(
        intersect_new=Intersection(entity_target.geometry, 'geometry'),
        intersect_old=Intersection('geometry', entity_target.geometry)
    ).annotate(
        overlap_new=ExpressionWrapper(
            Area('intersect_new') / Area('geometry'),
            output_field=FloatField()
        ),
        overlap_old=ExpressionWrapper(
            Area('intersect_old') / entity_target.geometry.area,
            output_field=FloatField()
        )
    )
    if above_thresholds_only:
        old_entities = old_entities.filter(
            Q(overlap_new__gt=threshold_new) &
            Q(overlap_old__gt=threshold_old)
        )

    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('get_closest_entities', end - start)

    return old_entities.count(), old_entities.annotate(
        overlap_weight=Case(
            When(
                Q(overlap_new__gt=threshold_new) &
                Q(overlap_old__gt=threshold_old),
                then=(F('overlap_new') + F('overlap_old'))
            ),
            default=(F('overlap_new') + F('overlap_old')) / 2,
        )
    ).order_by('-overlap_weight', '-start_date')


def compare_entities(
        entity_target: GeographicalEntity,
        entity_source: GeographicalEntity,
        **kwargs):
    """
    entity_target -> mainBoundary: new entity
    entity_source -> comparisonBoundary: selected from user
    Return: {
        geometry_overlap_new: 90.9,
        geometry_overlap_old: 90.9,
        same_entity: true,
        code_match: true,
        name_similarity: 99.0,
        main_boundary_data: {
            label: 'ABC',
            area: 90,
            perimeter: 90,
            code: 'AAA'
        },
        comparison_boundary_data: {
            label: 'ABC',
            area: 90,
            perimeter: 90,
            code: 'AAA'
        }
    }
    """
    start = time.time()
    if not entity_target.area:
        entity_target.area = area(
            entity_target.geometry.geojson
        ) / 1e+6
        entity_target.save()
    if not entity_source.area:
        entity_source.area = area(
            entity_source.geometry.geojson
        ) / 1e+6
        entity_source.save()
    intersection_new = entity_target.geometry.intersection(
        entity_source.geometry
    )
    geometry_overlap_new = (
        intersection_new.area / entity_source.geometry.area
    )
    intersection_old = entity_source.geometry.intersection(
        entity_target.geometry
    )
    geometry_overlap_old = (
        intersection_old.area / entity_target.geometry.area
    )
    code_match = AdminBoundaryMatching.check_code(entity_target, entity_source)
    name_similarity = AdminBoundaryMatching.name_similarity(
        entity_target,
        entity_source
    )
    same_entity = check_is_same_entity(
        entity_target.dataset,
        geometry_overlap_new,
        geometry_overlap_old
    )

    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('compare_entities', end - start)

    return {
        'geometry_overlap_new': geometry_overlap_new,
        'geometry_overlap_old': geometry_overlap_old,
        'same_entity': 'Yes' if same_entity else 'No',
        'code_match': code_match,
        'name_similarity': name_similarity,
        'main_boundary_data': {
            'label': entity_target.label,
            'area': round(entity_target.area, 2),
            'perimeter': round(entity_target.geometry.length, 2),
            'code': entity_target.unique_code
        },
        'comparison_boundary_data': {
            'label': entity_source.label,
            'area': round(entity_source.area, 2),
            'perimeter': round(entity_source.geometry.length, 2),
            'code': entity_source.unique_code,
            'version': get_version_code(entity_source.unique_code_version),
            'level': entity_source.level
        }
    }


def recalculate_summary(entity_upload: EntityUploadStatus, **kwargs):
    """Recalculate summary data after rematch"""
    start = time.time()
    admin_boundary_matching = AdminBoundaryMatching(entity_upload)
    ancestor_entity = entity_upload.revised_geographical_entity
    admin_boundary_matching.new_entities = (
        ancestor_entity.
        all_children().filter(
            layer_file__in=entity_upload.upload_session
            .layerfile_set.all(),
        ).order_by('level', 'label')
    )
    summary = admin_boundary_matching.generate_summary_data()
    entity_upload.comparison_data_ready = True
    entity_upload.boundary_comparison_summary = (
        summary
    )
    entity_upload.save()

    end = time.time()
    if kwargs.get('log_object'):
        kwargs.get('log_object').add_log('recalculate_summary', end - start)

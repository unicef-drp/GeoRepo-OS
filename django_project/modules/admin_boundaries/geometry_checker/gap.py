from typing import Tuple, List
import math
from django.db.models import QuerySet
from django.contrib.gis.db.models import Union
from django.contrib.gis.geos import (
    GEOSGeometry
)
from georepo.models import GeographicalEntity
from .qrectangle import QRectangle
from .geometry_check_errors import GapCheckError
from .geometry_utils import (
    part_count,
    part_at
)


def gap_check(
        geom_queryset: QuerySet[GeographicalEntity],
        tolerance: float,
        gap_threshold_map_units: float,
        reduced_tolerance: float = None) -> Tuple[List[GapCheckError], str]:
    errors: List[GapCheckError] = []
    if reduced_tolerance is None:
        # use root square from tolerance
        # this is tolerance for area
        reduced_tolerance = math.sqrt(tolerance)
    # get union of geometry
    union_geom_qs = geom_queryset.aggregate(Union('geometry'))
    union_geom: GEOSGeometry = union_geom_qs['geometry__union']
    if not union_geom:
        return errors, 'Unable to create union from the geometries'
    # get the envelop of union
    envelop: GEOSGeometry = union_geom.envelope
    # buffer the envelop with style
    # end cap style = square (3)
    # join style = mitre (2) with mitre ratio 4.0
    envelop = envelop.buffer_with_style(2, 0, 3, 2, 4.0)
    # find envelop bbox and snapped to grid
    spacing_grid = tolerance
    envelop_bbox = QRectangle.from_tuple(envelop.extent)
    envelop_bbox = envelop_bbox.snapped_to_grid(spacing_grid)

    # Compute difference between envelope and union to obtain gap polygons
    diff_geom: GEOSGeometry = envelop.difference(union_geom)

    # For each gap polygon which does not lie on the boundary,
    # get neighboring polygons and add error
    n_parts = part_count(diff_geom)
    for i_part in range(n_parts):
        gap_geom = part_at(diff_geom, i_part)
        # Skip the gap between features and boundingbox
        gap_geom_bbox = QRectangle.from_tuple(gap_geom.extent)
        gap_geom_bbox = gap_geom_bbox.snapped_to_grid(spacing_grid)
        if gap_geom_bbox == envelop_bbox:
            continue
        # Skip gaps above threshold
        gap_geom_area = gap_geom.area
        if (
            (gap_threshold_map_units > 0 and
             gap_geom_area > gap_threshold_map_units) or
            gap_geom_area < reduced_tolerance
        ):
            continue
        # Get neighboring polygons
        neighboring_ids = []
        gap_area_bbox: QRectangle = QRectangle.from_tuple(gap_geom.extent)
        other_geometries = geom_queryset.filter(
            geometry__bboverlaps=gap_geom
        )
        for geom in other_geometries:
            if gap_geom.distance(geom.geometry) < tolerance:
                neighboring_ids.append({
                    'id': geom.id,
                    'feature_id': geom.internal_code,
                    'label': geom.label
                })
                gap_area_bbox.combine_extent_with(
                    QRectangle.from_tuple(geom.geometry.extent)
                )
        if len(neighboring_ids) == 0:
            continue
        # add error
        errors.append(
            GapCheckError(gap_geom, neighboring_ids, gap_geom_area,
                          gap_geom_bbox, gap_area_bbox)
        )
    return errors, None

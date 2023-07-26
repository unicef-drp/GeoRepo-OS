from typing import List
from django.contrib.gis.geos import (
    GEOSGeometry
)
from .qvector import QVector


class SingleGeometryCheckError(object):

    def __init__(self, errors: List[GEOSGeometry] | List[QVector],
                 part=-1, ring=-1, vertex=-1) -> None:
        self.errors = errors
        self.part = part
        self.ring = ring
        self.vertex = vertex


class OverlapCheckError(object):

    def __init__(self, feature_id, feature_name,
                 overlap_geom: GEOSGeometry, overlap_area: float) -> None:
        self.feature_id = feature_id
        self.feature_name = feature_name
        self.overlap_geom = overlap_geom
        self.overlap_area = overlap_area


class GapCheckError(object):

    def __init__(self, gap_geom: GEOSGeometry, neighboring_ids,
                 gap_area, gap_bbox, gap_area_bbox) -> None:
        self.gap_geom = gap_geom
        self.neighboring_ids = neighboring_ids
        self.gap_area = gap_area
        self.gap_bbox = gap_bbox
        self.gap_area_bbox = gap_area_bbox
        self.error_location = gap_geom.centroid


class InvalidGeometryNodesError(object):

    def __init__(self, feature_id, error) -> None:
        self.feature_id = feature_id
        self.error = error


class ContainedCheckError(object):

    def __init__(self, feature_id, other_feature_id) -> None:
        self.feature_id = feature_id
        self.other_feature_id = other_feature_id

    def __str__(self) -> str:
        return f'{self.feature_id} - {self.other_feature_id}'


class DuplicateCheckError(object):

    def __init__(self, feature_id, other_feature_id) -> None:
        self.feature_id = feature_id
        self.other_feature_id = other_feature_id

    def __str__(self) -> str:
        return f'{self.feature_id} - {self.other_feature_id}'

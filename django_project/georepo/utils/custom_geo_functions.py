from django.contrib.gis.db.models.functions import ForcePolygonCW, Centroid
from django.db.models.expressions import fields


class ForcePolygonCCW(ForcePolygonCW):
    """To correct geojson output that satisfy right hand rule"""
    function = 'ST_ForcePolygonCCW'


class CentroidGravity(Centroid):
    """Calculate the gravity centroid"""
    function = 'ST_PointOnSurface'


class GeometryAsText(Centroid):
    """Geometry as text"""
    function = 'ST_AsText'
    output_field = fields.CharField()

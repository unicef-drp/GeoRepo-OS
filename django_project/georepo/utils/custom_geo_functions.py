from django.contrib.gis.db.models.functions import ForcePolygonCW, Centroid


class ForcePolygonCCW(ForcePolygonCW):
    """To correct geojson output that satisfy right hand rule"""
    function = 'ST_ForcePolygonCCW'


class CentroidGravity(Centroid):
    """Calculate the gravity centroid"""
    function = 'ST_PointOnSurface'

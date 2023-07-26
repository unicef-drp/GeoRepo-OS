from rest_framework.renderers import JSONRenderer


class GeojsonRenderer(JSONRenderer):
    format = 'geojson'


class ShapefileRenderer(JSONRenderer):
    format = 'shapefile'


class KmlRenderer(JSONRenderer):
    format = 'kml'


class TopojsonRenderer(JSONRenderer):
    format = 'topojson'

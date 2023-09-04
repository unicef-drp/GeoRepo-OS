from georepo.utils.fiona_utils import open_collection_by_file


def extract_gpkg_attributes(layer_file):
    """
    Load and read geopackage file, and returns all the attributes
    :param layer_file_path: path of the layer file
    :return: list of attributes, e.g. ['id', 'name', ...]
    """
    attrs = []
    with open_collection_by_file(layer_file, 'GPKG') as collection:
        try:
            attrs = next(iter(collection))["properties"].keys()
        except (KeyError, IndexError):
            pass
    return attrs


def get_gpkg_feature_count(layer_file):
    """
    Get Feature count in shape file
    """
    feature_count = 0
    with open_collection_by_file(layer_file, 'GPKG') as collection:
        feature_count = len(collection)
    return feature_count

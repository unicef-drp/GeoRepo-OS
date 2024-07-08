
# ordering API
API_ORDERS = {
    "01-search-module": [],
    "02-search-dataset": [
        "search-dataset-list",
        "search-dataset-detail"
    ],
    "03-search-view": [],
    "04-search-view-entity": [
        "search-entity-by-ucode",
        "search-entity-by-concept-ucode",
        "search-view-entity-by-id",
        "search-view-entity-by-level",
        "search-view-entity-by-level-and-ucode",
        "search-view-entity-by-level-and-concept-ucode",
        "search-view-entity-by-level-0",
        "search-view-entity-by-type",
        "search-view-entity-by-type-and-ucode",
        "search-view-entity-versions-by-ucode",
        "search-view-entity-versions-by-concept-ucode",
        "search-view-entity-by-name",
        "search-view-entity-children-by-ucode",
        "search-view-entity-parents-by-ucode",
        "search-view-entity-by-geometry",
        "batch-search-view-by-id",
        "check-batch-status-search-view-by-id",
        "get-result-batch-search-view-by-id",
    ],
    "05-operation-view-entity": [
        "operation-view-bbox",
        "operation-view-containment-check",
        "batch-geocoding",
        "check-status-batch-geocoding",
        "get-result-batch-geocoding"
    ],
    "06-download": [
        "submit-download-job",
        "fetch-download-job-status"
    ],
    "07-controlled-list": []
}


API_METHODS = ['get', 'post', 'put', 'delete']


def find_api_method(pathItem):
    """Find api method from openapi.PathItem."""
    for method in API_METHODS:
        pathMethod = pathItem.get(method, None)
        if pathMethod is not None:
            return method, pathMethod
    return None, None


def find_api_idx(tag, pathItem):
    """Find api index from API_ORDERS."""
    if tag not in API_ORDERS:
        return 0
    operationId = pathItem.get('operationId', None)
    if operationId is None:
        return 0
    if len(API_ORDERS[tag]) == 0:
        return 0
    return API_ORDERS[tag].index(operationId)

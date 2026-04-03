
# ordering API
API_ORDERS = {
    "00-search-entity": [
        "search-entity-by-ucode",
        "search-entity-by-concept-ucode"
    ],
    "01-search-module": [],
    "02-search-dataset": [
        "search-dataset-list",
        "search-dataset-detail"
    ],
    "03-search-dataset-entity": [
        "search-entity-by-id",
        "search-entity-by-level",
        "search-entity-by-level-and-ucode",
        "search-entity-by-level-and-concept-ucode",
        "search-entity-by-level-0",
        "search-entity-by-type",
        "search-entity-by-type-and-ucode",
        "search-dataset-entity-by-ucode",
        "search-dataset-entity-by-concept-ucode",
        "search-entity-versions-by-ucode",
        "search-entity-versions-by-concept-ucode",
        "search-entity-by-name",
        "search-entity-children-by-ucode",
        "search-entity-parents-by-ucode",
        "search-entity-by-geometry",
        "search-dataset-hierarchical",
        "batch-search-entity-by-id",
        "batch-status-search-entity-by-id",
        "batch-result-search-entity-by-id",
    ],
    "04-operation-dataset-entity": [
        "operation-bbox",
        "operation-bbox-post",
        "operation-containment-check",
        "entity-batch-geocoding",
        "entity-check-status-batch-geocoding",
        "entity-get-result-batch-geocoding"
    ],
    "05-search-view": [
        "search-view-list",
        "search-view-list-by-dataset",
        "search-view-detail",
        "search-view-centroid"
    ],
    "06-search-view-entity": [
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
        "batch-status-search-view-by-id",
        "batch-result-search-view-by-id",
    ],
    "07-operation-view-entity": [
        "operation-view-bbox",
        "operation-view-bbox-post",
        "operation-view-containment-check",
        "batch-geocoding",
        "check-status-batch-geocoding",
        "get-result-batch-geocoding"
    ],
    "08-download": [
        "submit-download-dataset-job",
        "fetch-download-dataset-job-status",
        "submit-download-view-job",
        "fetch-download-view-job-status"
    ],
    "09-controlled-list": []
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

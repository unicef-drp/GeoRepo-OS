import uuid
import io
import csv
import random
from django.db.models.expressions import RawSQL
from georepo.models.dataset import Dataset
from georepo.models.dataset_view import DatasetView
from georepo.models.entity import GeographicalEntity


def generate_jmeter_scripts():
    """
    Return zip file containing all scripts
    """
    results = {}
    # write to Class01SearchModuleApi.csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['testCase', 'httpStatusCode', 'page', 'pageSize'])
    writer.writerow(['Success', '200', '1', '50'])
    results['Class01SearchModuleApi.csv'] = output.getvalue()

    datasets = Dataset.objects.exclude(
        module__isnull=True
    )
    datasets = list(datasets)
    dataset = random.choice(datasets)
    # write to Class02SearchDatasetApi.csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'testCase', 'httpStatusCode', 'uuid', 'cached',
        'datasetListhttpStatusCode', 'moduleUuid', 'page',
        'pageSize', 'cached'
    ])
    writer.writerow([
        'Success', 200, str(dataset.uuid), 'true',
        200, str(dataset.module.uuid), 1, 10, 'true'
    ])
    writer.writerow([
        'NotFound', 404, str(uuid.uuid4()), 'true',
        200, str(uuid.uuid4()), 1, 10, 'true'
    ])
    writer.writerow([
        'BadRequest', 404, '123123', 'true',
        400, '123123', 1, 10, 'true'
    ])
    writer.writerow([
        'BadRequest', 404, '123123aaa', 'true',
        404, 'xxxvxcv', 1, 10, 'true'
    ])
    results['Class02SearchDatasetApi.csv'] = output.getvalue()

    dataset_views = list(
        DatasetView.objects.filter(
            dataset=dataset
        )
    )
    view = random.choice(dataset_views)
    # write to Class03SearchViewApi.csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'testCase', 'httpStatusCode', 'uuid', 'cached',
        'viewListhttpStatusCode', 'datasetUuid', 'page',
        'pageSize', 'cached'
    ])
    writer.writerow([
        'Success', 200, str(view.uuid), 'true',
        200, str(dataset.uuid), 1, 10, 'true'
    ])
    writer.writerow([
        'BadRequest', 400, '123123', 'true',
        400, '123sefsdf', 1, 10, 'true'
    ])
    writer.writerow([
        'NotFound', 404, str(uuid.uuid4()), 'true',
        200, str(uuid.uuid4()), 1, 10, 'true'
    ])
    writer.writerow([
        'BadRequest', 404, 'xxxvxcv', 'true',
        404, 'xxxvxcv', 1, 10, 'true'
    ])
    results['Class03SearchViewApi.csv'] = output.getvalue()
    # find 1 entity from view
    entities = GeographicalEntity.objects.filter(
        dataset=dataset,
        is_approved=True
    )
    raw_sql = (
        'SELECT id from "{}"'
    ).format(str(view.uuid))
    entities = entities.filter(
        id__in=RawSQL(raw_sql, [])
    ).values_list('id', flat=True)
    if entities:
        entity_id = random.choice(list(entities))
        entity = GeographicalEntity.objects.get(id=entity_id)
        # write to Class04SearchViewEntityApi.csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'testCase', 'httpStatusCode', 'uuid', 'data', 'level',
            'is_latest', 'page', 'pageSize', 'cached', 'geom', 'format',
            'id_type', 'id', 'admin_level', 'ucode', 'search_text',
            'entity_type', 'concept_uuid', 'timestamp'
        ])
        writer.writerow([
            'Success', 200, str(view.uuid), '{}', 1, 'true', 1, 30,
            'true', 'no_geom', 'json', 'uuid', str(entity.uuid_revision),
            entity.level, entity.ucode, entity.label, entity.type.label,
            str(entity.uuid), entity.start_date.isoformat()
        ])
        results['Class04SearchViewEntityApi.csv'] = output.getvalue()
        # write to Class05OperationViewEntityApi.csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'testCase', 'httpStatusCode', 'uuid',
            'id_type', 'id', 'checkHttpStatusCode', 'spatial_query',
            'distance', 'admin_level'
        ])
        writer.writerow([
            'Success', 200, str(view.uuid),
            'uuid', str(entity.uuid_revision),
            200, 'ST_Intersects',
            0, entity.level
        ])
        results['Class05OperationViewEntityApi.csv'] = output.getvalue()
    # write to Class07ControlledlistApi.csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['testCase', 'httpStatusCode'])
    writer.writerow(['Success', '200'])
    results['Class07ControlledlistApi.csv'] = output.getvalue()
    return results

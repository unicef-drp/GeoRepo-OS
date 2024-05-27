from typing import Tuple, List
from django.contrib.gis.geos import Point
from georepo.utils.entity_query import validate_datetime
from georepo.models import (
    Dataset, DatasetView
)

from dashboard.models import (
    EntitiesUserConfig
)


def generate_query_condition(
        dataset: Dataset,
        filter: EntitiesUserConfig,
        privacy_level: int = None) -> Tuple[str, List[str]]:
    sql = ''
    query_values = [dataset.id]
    if privacy_level is not None:
        sql = (
            sql + 'AND gg.privacy_level <= %s ')
        query_values.append(privacy_level)
    if ('country' in filter.filters and
            len(filter.filters['country']) > 0):
        sql = (
            sql + 'AND (parent_0.label IN %s OR '
            '(gg.ancestor_id IS NULL AND gg.label IN %s)) '
        )
        query_values.append(tuple(filter.filters['country']))
        query_values.append(tuple(filter.filters['country']))
    if 'type' in filter.filters and len(filter.filters['type']) > 0:
        sql = (
            sql + 'AND ge.label IN %s ')
        query_values.append(tuple(filter.filters['type']))
    if ('level' in filter.filters and
            len(filter.filters['level']) > 0):
        sql = (
            sql + 'AND gg.level IN %s ')
        query_values.append(tuple(filter.filters['level']))
    if ('admin_level_name' in filter.filters and
            len(filter.filters['admin_level_name']) > 0):
        sql = (
            sql + 'AND gg.admin_level_name IN %s ')
        query_values.append(tuple(filter.filters['admin_level_name']))
    if ('revision' in filter.filters and
            len(filter.filters['revision']) > 0):
        sql = (
            sql + 'AND gg.revision_number IN %s ')
        query_values.append(tuple(filter.filters['revision']))
    if ('status' in filter.filters and
            len(filter.filters['status']) > 0):
        if ('Pending' in filter.filters['status'] and
                'Approved' in filter.filters['status']):
            # ignore since pending and approved are contradict
            pass
        elif ('Pending' in filter.filters['status']):
            sql = (
                sql + 'AND (gg.is_approved=false OR '
                'gg.is_approved IS NULL) '
            )
        elif ('Approved' in filter.filters['status']):
            sql = sql + 'AND gg.is_approved=true '
    if ('valid_from' in filter.filters):
        valid_from = validate_datetime(filter.filters['valid_from'])
        if (valid_from):
            sql = (
                sql + 'AND (gg.start_date<=%s AND '
                '(gg.end_date IS NULL OR gg.end_date>=%s)) '
            )
            query_values.append(valid_from)
            query_values.append(valid_from)
    if 'privacy_level' in filter.filters and \
        len(filter.filters['privacy_level']) > 0:
        sql = (
            sql + 'AND gg.privacy_level IN %s ')
        query_values.append(tuple(filter.filters['privacy_level']))
    if 'source' in filter.filters and \
        len(filter.filters['source']) > 0:
        sql = (
            sql + 'AND gg.source IN %s ')
        query_values.append(tuple(filter.filters['source']))
    if ('search_text' in filter.filters and
            len(filter.filters['search_text']) > 0):
        sql = (
            sql + 'AND (gg.label ilike %s OR '
            'parent_0.label ilike %s OR '
            'gg.unique_code ilike %s OR '
            'gg.concept_ucode ilike %s OR '
            'ge_id.value ilike %s OR '
            'ge_name.name ilike %s  OR '
            'gg.internal_code ilike %s  OR '
            'gg.source ilike %s  OR '
            'gg.admin_level_name ilike %s)'
        )

        search_text = '%' + filter.filters['search_text'] + '%'
        for i in range(9):
            query_values.append(search_text)

    if 'points' in filter.filters:
        points_cond = []
        for lngLat in filter.filters['points']:
            point = Point(lngLat[0], lngLat[1], srid=4326)
            points_cond.append('ST_Intersects(gg.geometry, %s)')
            query_values.append(point.ewkt)
        if points_cond:
            sql = (
                sql + 'AND (' + ' OR '.join(points_cond) + ') '
            )
    # filter by ancestor for review page
    if 'ancestor' in filter.filters and len(filter.filters['ancestor']) > 0:
        if (
            'level' in filter.filters and
            len(filter.filters['level']) == 1 and
            int(filter.filters['level'][0]) == 0
        ):
            sql = (
                sql + 'AND gg.uuid_revision = %s ')
            query_values.append(filter.filters['ancestor'][0])
        else:
            sql = (
                sql + 'AND parent_0.uuid_revision IN %s ')
            query_values.append(tuple(filter.filters['ancestor']))
    return sql, query_values


def generate_entity_query(
        dataset: Dataset,
        filter: EntitiesUserConfig,
        sort_by=None,
        sort_direction=None,
        privacy_level=None) -> Tuple[str, List[str]]:
    sql_select = (
        'SELECT gg.id as id, '
        'case '
        'when gg.ancestor_id is not null then parent_0.label '
        'else gg.label '
        'end country, '
        'gg.level as level, ge.label as type, gg.label, '
        'gg.internal_code, '
        "CASE WHEN gg.unique_code IS NULL OR gg.unique_code='' "
        "THEN '-' ELSE "
        "gg.unique_code || '_V' || CASE WHEN "
        'gg.unique_code_version IS NULL THEN 1 ELSE '
        'gg.unique_code_version END '
        'END as unique_code, '
        "CASE WHEN gg.concept_ucode IS NULL OR gg.concept_ucode='' "
        "THEN '-' ELSE "
        'gg.concept_ucode END as concept_ucode, '
        'gg.start_date, '
        'gg.revision_number, '
        'case '
        'when gg.is_approved then \'Approved\' '
        'else \'Pending\' '
        'end status, '
        '\'\' as centroid, '
        'gg.unique_code_version, '
        'gg.is_latest, '
        'gg.approved_date, '
        'gg.source, '
        'gg.admin_level_name, '
        'gg.privacy_level, '
        'string_agg(distinct auth_user.first_name || \' \' '
        '|| auth_user.last_name, \', \') as approved_by, '
        'string_agg(distinct ge_name.name, \', \') as other_name, '
        'string_agg(distinct ge_id.value, \', \') as other_id '
    )
    sql_joins = (
        'from georepo_geographicalentity gg '
        'inner join georepo_entitytype ge on ge.id=gg.type_id '
        'left join georepo_geographicalentity parent_0 on ( '
        '    parent_0.id = gg.ancestor_id '
        ') '
        'left join georepo_entityid ge_id on '
        '    ge_id.geographical_entity_id = gg.id '
        'left join georepo_entityname ge_name on '
        '    ge_name.geographical_entity_id = gg.id '
        'left join auth_user auth_user on '
        '    auth_user.id = gg.approved_by_id '
    )
    sql_joins = sql_joins + 'where gg.dataset_id = %s '
    sql_cond, query_values = generate_query_condition(
        dataset,
        filter,
        privacy_level=privacy_level)
    if filter.query_string:
        query_string = filter.query_string.replace(';', '')
        query_string = query_string.replace('%', '%%')
        sql_cond = (
            sql_cond +
            ' AND gg.id IN (SELECT temp_table.id FROM (' +
            query_string +
            ') AS temp_table'
            ') '
        )
    sql = (
        sql_select + sql_joins + sql_cond +
        'group by gg.id, parent_0.id, ge.label, '
        'gg.level, gg.revision_number'
    )
    if sort_by and sort_direction:
        sql = (
            sql + f' ORDER BY {sort_by} {sort_direction}'
        )
    return sql, query_values


def generate_entity_query_map(
        dataset: Dataset,
        filter: EntitiesUserConfig,
        z: int,
        x: int,
        y: int,
        privacy_level=None,
        using_view_tiling_config=False,
        view_id=None) -> Tuple[str, List[str]]:
    sql_select = (
        '  SELECT gg.id, gg.label, gg.level, gg.unique_code, '
        '  gg.internal_code,'
        '  ST_AsMVTGeom('
        '    ST_Transform('
        '      ges.simplified_geometry, 3857), '
        '    TileBBox(%s, %s, %s, 3857)) as geom '
    )
    sql_joins = (
        'from georepo_entitysimplified ges '
        'inner join georepo_geographicalentity gg on '
        '    gg.id=ges.geographical_entity_id '
    )
    if using_view_tiling_config:
        sql_joins = (
            sql_joins +
            'inner join georepo_datasetviewtilingconfig dtc on '
            '    dtc.dataset_view_id=%s and dtc.zoom_level=%s '
            'inner join georepo_viewadminleveltilingconfig tc on '
            '    tc.level=gg.level and '
            '    ges.simplify_tolerance=tc.simplify_tolerance and '
            '    tc.view_tiling_config_id = dtc.id '
        )
    else:
        sql_joins = (
            sql_joins +
            'inner join georepo_datasettilingconfig dtc on '
            '    dtc.dataset_id=gg.dataset_id and dtc.zoom_level=%s '
            'inner join georepo_adminleveltilingconfig tc on '
            '    tc.level=gg.level and '
            '    ges.simplify_tolerance=tc.simplify_tolerance and '
            '    tc.dataset_tiling_config_id = dtc.id '
        )
    sql_joins = (
        sql_joins +
        'inner join georepo_entitytype ge on ge.id=gg.type_id '
        'left join georepo_geographicalentity parent_0 on ( '
        '    parent_0.id = gg.ancestor_id '
        ') '
        'left join georepo_entityid ge_id on '
        '    ge_id.geographical_entity_id = gg.id '
        'left join georepo_entityname ge_name on '
        '    ge_name.geographical_entity_id = gg.id '
    )
    sql_joins = (
        sql_joins +
        'WHERE gg.dataset_id = %s '
        'AND ges.simplified_geometry && TileBBox(%s, %s, %s, 4326) '
    )
    sql_cond, query_values = generate_query_condition(
        dataset,
        filter,
        privacy_level=privacy_level)
    if filter.query_string:
        query_string = filter.query_string.replace(';', '')
        query_string = query_string.replace('%', '%%')
        sql_cond = (
            sql_cond +
            ' AND gg.id IN (SELECT temp_table.id FROM (' +
            query_string +
            ') AS temp_table'
            ') '
        )
    if filter.concept_ucode:
        sql_cond = (
            sql_cond +
            ' AND gg.concept_ucode = %s '
        )
        query_values.append(filter.concept_ucode)
    sql = (
        sql_select + sql_joins + sql_cond +
        'group by gg.id, ges.simplified_geometry'
    )
    # note: if map, then query_values needs to be added with
    # z, x, y + z, z + z, x, y
    # second tilebox args
    query_values.insert(1, y)
    query_values.insert(1, x)
    query_values.insert(1, z)
    # zoom filters
    query_values.insert(0, z)
    if using_view_tiling_config:
        query_values.insert(0, view_id)
    # first tilebox args
    query_values.insert(0, y)
    query_values.insert(0, x)
    query_values.insert(0, z)
    return sql, query_values


def generate_entity_query_map_for_view(
        dataset_view: DatasetView,
        filter: EntitiesUserConfig,
        z: int,
        x: int,
        y: int,
        privacy_level=None) -> Tuple[str, List[str]]:
    # check for existing tiling configs
    view_tiling_config = dataset_view.datasetviewtilingconfig_set.exists()
    sql, query_values = (
        generate_entity_query_map(
            dataset_view.dataset,
            filter,
            z,
            x,
            y,
            privacy_level=privacy_level,
            using_view_tiling_config=view_tiling_config,
            view_id=dataset_view.id
        )
    )
    return sql, query_values


def generate_entity_query_map_for_temp(
        session: str,
        dataset: Dataset,
        z: int,
        x: int,
        y: int,
        privacy_level=None,
        dataset_view: DatasetView = None) -> Tuple[str, List[str]]:
    """Generate query map for preview tiling configs."""
    sql_select = (
        '  SELECT gg.id, gg.label, gg.level, gg.unique_code, '
        '  gg.internal_code,'
        '  CASE WHEN ges.simplified_geometry is NULL '
        '  THEN ST_AsMVTGeom('
        '    ST_Transform('
        '      simplifygeometry(gg.geometry, ttc.simplify_tolerance), 3857), '
        '    TileBBox(%s, %s, %s, 3857)) '
        '  ELSE ST_AsMVTGeom('
        '    ST_Transform('
        '      ges.simplified_geometry, 3857), '
        '    TileBBox(%s, %s, %s, 3857)) '
        'END as geom '
    )
    sql_joins = (
        'from georepo_geographicalentity gg '
        'inner join georepo_temporarytilingconfig ttc on '
        '    ttc.session=%s and ttc.zoom_level=%s and ttc.level=gg.level '
        'left join georepo_entitysimplified ges on '
        '    gg.id=ges.geographical_entity_id and '
        '    ges.simplify_tolerance=ttc.simplify_tolerance '
    )
    sql_joins = (
        sql_joins +
        'WHERE gg.dataset_id = %s '
        'AND gg.geometry && TileBBox(%s, %s, %s, 4326) '
    )
    query_values = [
        z, x, y,
        z, x, y,
        session, z,
        dataset.id, z, x, y
    ]
    sql_cond = ''
    if privacy_level is not None:
        sql_cond = (
            sql_cond + 'AND gg.privacy_level <= %s ')
        query_values.append(privacy_level)
    if dataset_view:
        query_string = dataset_view.query_string.replace(';', '')
        query_string = query_string.replace('%', '%%')
        sql_cond = (
            sql_cond +
            ' AND gg.id IN (SELECT temp_table.id FROM (' +
            query_string +
            ') AS temp_table'
            ') '
        )
    sql = (
        sql_select + sql_joins + sql_cond
    )
    return sql, query_values

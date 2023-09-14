import React, {useState, useEffect} from 'react';
import {
    Box,
    Grid,
    Skeleton
} from "@mui/material";
import {useSearchParams} from "react-router-dom";
import "../../styles/DatasetEntities.scss";
import {
    EntitiesFilterInterface,
    getDefaultFilter,
    EntitiesFilterUpdateInterface
} from './EntitiesFilter';
import EntitiesMap, {EntityItemInterface} from './EntitiesMap';
import EntitiesTable from './EntitiesTable';
import axios from "axios";
import {useAppDispatch} from "../../app/hooks";
import {updateMenu, changeCurrentDataset} from "../../reducers/breadcrumbMenu";
import {setModule} from "../../reducers/module";
import toLower from "lodash/toLower";
import Dataset from '../../models/dataset';

const FILTER_API_URL = '/api/dashboard-dataset-filter/'
const GEOM_API_URL = '/api/dashboard-dataset/detail/'

interface DatasetEntitiesInterface {
    dataset?: Dataset,
    datasetId?: string,
    session?: string,
    mapProps?: any,
    datasetUuid?: string,
    datasetStyleSourceName?: string,
    viewUuid?: string
}

export default function DatasetEntities(props: DatasetEntitiesInterface) {
    const dispatch = useAppDispatch();
    const [searchParams, setSearchParams] = useSearchParams()
    const [datasetId, setDatasetId] = useState(null)
    const [datasetUuid, setDatasetUuid] = useState<string>('')
    const [datasetStyleSourceName, setDatasetStyleSourceName] = useState<string>('')
    const [session, setSession] = useState<string>('')
    const [filter, setFilter] = useState<EntitiesFilterInterface>(getDefaultFilter())
    const [selectedGeom, setSelectedGeom] = useState<any>(null)
    const [selectedBbox, setSelectedBbox] = useState<any>(null)
    const [selectedEntityIdOnHover, setSelectedEntityIdOnHover] = useState<EntityItemInterface>({id:0, level:0})
    const [filterLoading, setFilterLoading] = useState<boolean>(true)
    const [editable, setEditable] = useState<boolean>(false)

    const fetchDatasetDetail = (dataset_id:any) => {
        axios.get(`/api/dataset-detail/${dataset_id}`).then(
            response => {
                if (searchParams.get('id')) {
                    let _module_name = toLower(response.data.type.replace(' ', '_'))
                    let _name = response.data.dataset
                    if (response.data.type) {
                        _name = _name + ` (${response.data.type})`
                    }
                    dispatch(updateMenu({
                        id: `${_module_name}_dataset_entities`,
                        name: _name,
                        link: `/${_module_name}/dataset_entities`
                    }))
                    dispatch(setModule(_module_name))
                }
                setDatasetUuid(response.data.uuid)
                setDatasetStyleSourceName(response.data.source_name)
            }
        )
    }

    useEffect(() => {
        let _dataset_id = null
        if (props.datasetId) {
            // this is from View Preview
            _dataset_id = props.datasetId
            setDatasetUuid(props.datasetUuid)
            setDatasetStyleSourceName(props.datasetStyleSourceName)
        } else if (props.dataset) {
            // this is from Dataset Detail Preview
            _dataset_id = props.dataset.id
            setDatasetUuid(props.dataset.uuid)
            setDatasetStyleSourceName(props.dataset.source_name)
            setEditable(props.dataset.permissions.includes('Manage'))
        } else {
            _dataset_id = searchParams.get('id')
            fetchDatasetDetail(_dataset_id)
            dispatch(changeCurrentDataset(searchParams.get('id')))
        }
        setDatasetId(_dataset_id)        
        fetchFilter(_dataset_id)
      }, [searchParams, props.datasetId, props.dataset])

    const fetchFilter = (dataset_id: any) => {
        let _session = session
        if (_session === '' && props.session)
            _session = props.session
        let _query_params = `session=${_session}`
        if (props.viewUuid) {
            _query_params = _query_params + `&view_uuid=${props.viewUuid}`
        }
        axios.get(
            `${FILTER_API_URL}${dataset_id}/?${_query_params}`
            ).then(response => {
                if (session !== response.data['session']) {
                    setSession(response.data['session'])
                }
                const filters = response.data['filters']
                filters['updated_at'] = new Date()
                if (filters['valid_from'] != null)
                    filters['valid_from'] = new Date(filters['valid_from'])
                if (filters['valid_to'] != null)
                    filters['valid_to'] = new Date(filters['valid_to'])
                setFilter(filters)
                setFilterLoading(false)
            }
        ).catch(error => {
            console.log('fetchFilter Error ', error)
        })
    }

    const fetchGeomDetail = (id: number) => {
        let _query_params = ''
        if (props.viewUuid) {
            _query_params = _query_params + `view_uuid=${props.viewUuid}`
        }
        axios.get(`${GEOM_API_URL}${datasetId}/entity/${id}/?${_query_params}`).then(
            response => {
                setSelectedBbox(response.data['bbox'])
                setSelectedGeom(response.data['geom'])
            }
        ).catch(error => {
            console.log('fetchGeomDetail Error ', error)
        })
    }

    const onFilterChanged = (data: EntitiesFilterUpdateInterface) => {
        if (data.type === 'string_array') {
            setFilter({
                ...filter,
                [data.criteria]: data.values,
                updated_at: new Date()
            })
        } else if (data.type === 'string_search') {
            setFilter({
                ...filter,
                [data.criteria]: data.values[0],
                updated_at: new Date()
            })
        } else if (data.type === 'date_range') {
            setFilter({
                ...filter,
                valid_from: data.date_from,
                valid_to: data.date_to,
                updated_at: new Date()
            })
        }
    }

    const onFiltersChanged = (filters: EntitiesFilterUpdateInterface[]) => {
        let updated_filters:any = {...filter}
        for (let data of filters) {
            if (data.type === 'string_array') {
                updated_filters[data.criteria] = data.values
            } else if (data.type === 'string_search') {
                updated_filters[data.criteria] = data.values[0]
            } else if (data.type === 'date_range') {
                updated_filters.valid_from = data.date_from
                updated_filters.valid_to = data.date_to
            }
        }
        setFilter({
            ...filter,
            ...updated_filters,
            updated_at: new Date()
        })
    }

    const onTableLoadCompleted = (success: boolean) => {
        if (success) {
            setSelectedGeom(null)
        }
    }

    const onTableRowHover = (id: number, level: number, centroid?: any) => {
        setSelectedEntityIdOnHover({
            id:id,
            level:level,
            centroid:centroid
        })
    }

    const onMapEntityHover = (item: EntityItemInterface) => {
        setSelectedEntityIdOnHover(item)
    }

    const onMapFilterByPoints = (points: any[]) => {
        let updated_filters:any = {...filter}
        updated_filters['points'] = points
        setFilter({
            ...filter,
            ...updated_filters,
            updated_at: new Date()
        })
    }

    return (
        <Box sx={{ flexGrow: 1 }}>
            <Grid container flexDirection='row-reverse' id='dataset-entities-container'  spacing={1} flexWrap='nowrap'>
                <Grid item xs={6} md={5} id='dataset-entities-map' className='dataset-entities-item'>
                    { datasetId && datasetUuid && session && !filterLoading ? <EntitiesMap dataset_id={datasetId} session={session} filter_changed={filter.updated_at}
                        bbox={selectedBbox} selectedGeom={selectedGeom}
                        selectedEntityOnHover={selectedEntityIdOnHover}
                        entityOnMapHover={onMapEntityHover}
                        addFilterByPoints={onMapFilterByPoints}
                        initialMarkers={filter.points}
                        datasetUuid={datasetUuid}
                        styleSourceName={datasetStyleSourceName} {...props.mapProps} /> :
                        <Skeleton variant="rectangular" height={'100%'} width={'100%'}/>
                    }
                </Grid>
                <Grid item xs={6} md={7} id='dataset-entities-list' className='dataset-entities-item'>
                { datasetId && session && !filterLoading ?
                    <EntitiesTable
                      dataset_id={datasetId}
                      filter={filter}
                      session={session}
                      editable={editable}
                        onEntitySelected={fetchGeomDetail}
                        onLoadCompleted={onTableLoadCompleted}
                        onFilterUpdated={onFiltersChanged}
                        onSingleFilterUpdated={onFilterChanged}
                        onRowHover={onTableRowHover} viewUuid={props.viewUuid} />:
                    <Skeleton variant="rectangular" height={'100%'} width={'100%'}/>
                }
                </Grid>
            </Grid>
        </Box>
    )
}

import React, {useState, useEffect} from 'react';
import {
    Box,
    Grid,
    Skeleton,
    Typography
} from "@mui/material";
import {useSearchParams, useLocation} from "react-router-dom";
import "../../styles/DatasetEntities.scss";
import EntitiesMap, {EntityItemInterface} from './EntitiesMap';
import axios from "axios";
import List from "../../components/List";

const ENTITY_CUCODE_DETAIL_API_URL = '/api/dashboard-entity-by-cucode/detail/'
const GEOM_API_URL = '/api/dashboard-dataset/detail/'


interface ConceptUcodeDetailInterface {

}

interface EntityTableRowInterface {
    id: number,
    level: number,
    type: string,
    name: string,
    default_code: string,
    code: string,
    valid_from: Date,
    rev: number,
    status: string
}


export default function ConceptUcodeDetail(props: ConceptUcodeDetailInterface) {
    const { hash } = useLocation();
    const [searchParams, setSearchParams] = useSearchParams()
    const [datasetId, setDatasetId] = useState(null)
    const [datasetUuid, setDatasetUuid] = useState<string>('')
    const [datasetName, setDatasetName] = useState<string>('-')
    const [moduleName, setModuleName] = useState<string>('-')
    const [conceptUCode, setConceptUCode] = useState<string>('-')
    const [conceptUUID, setConceptUUID] = useState<string>('-')
    const [country, setCountry] = useState<string>('-')
    const [datasetStyleSourceName, setDatasetStyleSourceName] = useState<string>('-')
    const [data, setData] = useState<EntityTableRowInterface[]>([])
    const [session, setSession] = useState<string>('')
    const [sessionUpdatedAt, setSessionUpdatedAt] = useState(new Date())
    const [selectedGeom, setSelectedGeom] = useState<any>(null)
    const [selectedBbox, setSelectedBbox] = useState<any>(null)
    const [selectedEntityIdOnHover, setSelectedEntityIdOnHover] = useState<EntityItemInterface>({id:0, level:0})

    useEffect(() => {
        if (hash) {
            fetchEntityDetail(hash)
        } else if (searchParams.get('concept_ucode')) {
            fetchEntityDetail(searchParams.get('concept_ucode'))
        }
    }, [searchParams])

    const fetchEntityDetail = (entity_cucode: any) => {
        if (!(entity_cucode && entity_cucode.startsWith('#'))) {
            return
        }
        axios.get(`${ENTITY_CUCODE_DETAIL_API_URL}${encodeURIComponent(entity_cucode)}`).then(
            response => {
                if (response.data.entities && response.data.entities.length) {
                    setDatasetId(response.data.dataset_id)
                    setDatasetUuid(response.data.dataset_uuid)
                    setDatasetStyleSourceName(response.data.source_name)
                    setSession(response.data.session)
                    setData(response.data.entities as EntityTableRowInterface[])
                    setDatasetName(response.data.dataset_name)
                    setModuleName(response.data.module_name)
                    setConceptUCode(response.data.concept_ucode)
                    setConceptUUID(response.data.concept_uuid)
                    setCountry(response.data.country)
                }
            }
        )
    }

    const fetchGeomDetail = (id: number) => {
        axios.get(`${GEOM_API_URL}${datasetId}/entity/${id}/`).then(
            response => {
                setSelectedBbox(response.data['bbox'])
                setSelectedGeom(response.data['geom'])
            }
        ).catch(error => {
            console.log('fetchGeomDetail Error ', error)
        })
    }

    const onMapEntityHover = (item: EntityItemInterface) => {
        setSelectedEntityIdOnHover(item)
    }

    const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
        fetchGeomDetail(Number(rowData[0]))
    }

    return (
        <Box sx={{ flexGrow: 1 }}>
            <Grid container flexDirection='row-reverse' id='dataset-entities-container'  spacing={1} flexWrap='nowrap'>
                <Grid item xs={6} md={5} id='dataset-entities-map' className='dataset-entities-item'>
                    { datasetId && datasetUuid && session !== '' ? <EntitiesMap dataset_id={datasetId} session={session} filter_changed={sessionUpdatedAt}
                        bbox={selectedBbox} selectedGeom={selectedGeom}
                        selectedEntityOnHover={selectedEntityIdOnHover}
                        entityOnMapHover={onMapEntityHover}
                        datasetUuid={datasetUuid}
                        styleSourceName={datasetStyleSourceName} /> :
                        <Skeleton variant="rectangular" height={'100%'} width={'100%'}/>
                    }
                </Grid>
                <Grid item xs={6} md={7} id='dataset-entities-list' className='dataset-entities-item'>
                    <Grid container flexDirection={'column'} sx={{height: '100%'}}>
                        <Grid item>
                            <Grid container sx={{paddingTop: '20px', paddingBottom: '20px', paddingLeft: '10px', paddingRight: '10px'}}>
                                <Grid item md={2} xl={2} xs={12} sx={{ display: 'flex' }}>
                                    <Typography variant={'subtitle1'}>Concept UCode</Typography>
                                </Grid>
                                <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
                                    <Typography variant={'subtitle1'}>{conceptUCode}</Typography>
                                </Grid>
                                <Grid item md={2} xl={2} xs={12} sx={{ display: 'flex' }}>
                                    <Typography variant={'subtitle1'}>Concept UUID</Typography>
                                </Grid>
                                <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
                                    <Typography variant={'subtitle1'}>{conceptUUID}</Typography>
                                </Grid>
                                <Grid item md={2} xl={2} xs={12} sx={{ display: 'flex' }}>
                                    <Typography variant={'subtitle1'}>Country</Typography>
                                </Grid>
                                <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
                                    <Typography variant={'subtitle1'}>{country}</Typography>
                                </Grid>
                                <Grid item md={2} xl={2} xs={12} sx={{ display: 'flex' }}>
                                    <Typography variant={'subtitle1'}>Dataset</Typography>
                                </Grid>
                                <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
                                    <Typography variant={'subtitle1'}>{datasetName}</Typography>
                                </Grid>
                                <Grid item md={2} xl={2} xs={12} sx={{ display: 'flex' }}>
                                    <Typography variant={'subtitle1'}>Module</Typography>
                                </Grid>
                                <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
                                    <Typography variant={'subtitle1'}>{moduleName}</Typography>
                                </Grid>
                            </Grid>
                        </Grid>
                        <Grid item flexDirection={'column'} flex={1} sx={{display: 'flex'}}>
                            <Grid className={'entities-table-root'} container>
                                <Grid item className={'entities-table cucode-entities'}>
                                    <List
                                        pageName={'Entities'}
                                        listUrl={''}
                                        initData={data}
                                        selectionChanged={null}
                                        onRowClick={handleRowClick}
                                        excludedColumns={['id']}
                                    />
                                </Grid>
                            </Grid>
                        </Grid>
                    </Grid>
                </Grid>
            </Grid>
        </Box>
    )
}




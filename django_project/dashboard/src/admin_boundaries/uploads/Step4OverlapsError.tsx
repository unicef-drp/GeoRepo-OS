import React, {useEffect, useState, useRef} from "react";
import axios from "axios";
import Grid from '@mui/material/Grid';
import Button from '@mui/material/Button';
import Skeleton from '@mui/material/Skeleton';
import maplibregl, {AttributionControl} from "maplibre-gl";
import List from "../../components/List";
import { RowData } from "../../components/Table";
import Loading from "../../components/Loading";

const MIN_HEIGHT = 500;
const WINDOW_PREFERENCES: any = window.preferences
const MAPTILER_API_KEY = WINDOW_PREFERENCES ? WINDOW_PREFERENCES['maptiler_api_key'] : ''

const FETCH_ENTITY_OVERLAPS_URL = '/api/entity-upload-status/fetch-overlaps/'
const FETCH_ENTITY_OVERLAPS_DETAIL_URL = '/api/entity-upload-status/fetch-overlaps-detail/'
const MAP_STYLE_ORIGINAL_URL = `https://api.maptiler.com/maps/streets/style.json?key=${MAPTILER_API_KEY}`

interface OverlapsComparisonId {
    entityId1: number,
    entityId2: number
}

interface OverlapsErrorMapInterface {
    entityIds: OverlapsComparisonId
}

function OverlapsErrorMap(props: OverlapsErrorMapInterface) {
    const mapContainer = useRef(null);
    const map = useRef(null);
    const [lng] = useState(139.753);
    const [lat] = useState(35.6844);
    const [zoom] = useState(1);
    const [bbox, setBbox] = useState<any>(null)
    const [overlaps, setOverlaps] = useState<any>(null)
    const [geometry1, setGeometry1] = useState<any>(null)
    const [geometry2, setGeometry2] = useState<any>(null)
    const [mapLoaded, setMapLoaded] = useState(false)
    const [geom1Added, setGeom1Added] = useState<boolean>(false)
    const [geom2Added, setGeom2Added] = useState<boolean>(false)
    const [overlapsAdded, setOverlapsAdded] = useState<boolean>(false)
    const [loading, setLoading] = useState(true)

    const fetchEntityOverlapsDetail = (entity_id_1:  number, entity_id_2: number) => {
        axios.get(`${FETCH_ENTITY_OVERLAPS_DETAIL_URL}${entity_id_1}/${entity_id_2}/`).then(
            response => {
                setBbox(response.data['bbox'])
                setOverlaps(response.data['overlaps'])
                setGeometry1(response.data['geometry_1'])
                setGeometry2(response.data['geometry_2'])
            }, error => {
                console.log(error)
            }
        )
    }

    useEffect(() => {
        setTimeout(() => {
            setLoading(false)
        }, 200)
    }, []);

    useEffect(() => {
        if (props.entityIds && props.entityIds.entityId1 && props.entityIds.entityId2)
            fetchEntityOverlapsDetail(props.entityIds.entityId1, props.entityIds.entityId2)
    }, [props.entityIds])

    const mapFitBounds = () => {
        if (bbox && map.current) {
            map.current.fitBounds(
              bbox,
              {
                  padding: {top: 10, bottom:25, left: 20, right: 20}
              }
            )
        }
    }

    useEffect(() => {
        mapFitBounds()
    }, [bbox])

    useEffect(() => {
        if (!loading) {
            if (map.current) return; //stops map from intializing more than once
            let _style_url = MAP_STYLE_ORIGINAL_URL 
            map.current = new maplibregl.Map({
                container: mapContainer.current,
                style: _style_url,
                center: [lng, lat],
                zoom: zoom,
                attributionControl: false
            });
            map.current.addControl(new AttributionControl(), 'top-left');
            map.current.on('load', () => {
                setMapLoaded(true)
                mapFitBounds()
            })
        }
    }, [loading])

    useEffect(() => {
        if (!mapLoaded) return;
        // Draw geometry1
        if (geometry1) {
            if (map.current) {
                if (geom1Added) {
                    map.current.removeLayer('geom1');
                    map.current.removeSource('geom1');
                }
                map.current.addSource('geom1', {
                    'type': 'geojson',
                    'data': geometry1
                })
                setGeom1Added(true)
                map.current.addLayer({
                    'id': 'geom1',
                    'type': 'line',
                    'source': 'geom1',
                    'layout': {},
                    'paint': {
                        'line-color': '#32cd32',
                        'line-width': 6
                    }
                });
            }
        }
    }, [geometry1])

    useEffect(() => {
        if (!mapLoaded) return;
        // Draw geometry2
        if (geometry2) {
            if (map.current) {
                if (geom2Added) {
                    map.current.removeLayer('geom2');
                    map.current.removeSource('geom2');
                }
                map.current.addSource('geom2', {
                    'type': 'geojson',
                    'data': geometry2
                })
                setGeom2Added(true)
                map.current.addLayer({
                    'id': 'geom2',
                    'type': 'line',
                    'source': 'geom2',
                    'layout': {},
                    'paint': {
                        'line-color': '#32cd32',
                        'line-width': 6
                    }
                });
            }
        }
    }, [geometry2])

    useEffect(() => {
        if (!mapLoaded) return;
        // Draw geometry2
        if (overlaps) {
            if (map.current) {
                if (overlapsAdded) {
                    map.current.removeLayer('geomOverlaps');
                    map.current.removeSource('geomOverlaps');
                }
                map.current.addSource('geomOverlaps', {
                    'type': 'geojson',
                    'data': overlaps
                })
                setOverlapsAdded(true)
                map.current.addLayer({
                    'id': 'geomOverlaps',
                    'type': 'fill',
                    'source': 'geomOverlaps',
                    'layout': {},
                    'paint': {
                        'fill-color': '#ff0000',
                        'fill-opacity': 0.4
                    }
                });
            }
        }
    }, [overlaps])

    return (
        <div className="map-wrap">
            { loading ?
                <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> :
                <div ref={mapContainer} className="map" />}
          </div>
        )
}


export interface ViewOverlapInterface {
    upload_id: number,
    onBackClicked: () => void
}

interface OverlapItemInterface {
    level: number,
    id_1: number,
    label_1: string,
    default_code_1: string,
    id_2: number,
    label_2: string,
    default_code_2: string,
    overlaps_area: string
}

export default function Step4OverlapsError(props: ViewOverlapInterface) {
    const [loading, setLoading] = useState(false)
    const [data, setData] = useState<OverlapItemInterface[]>([])
    const [selectedEntityIds, setSelectedEntityIds] = useState<OverlapsComparisonId>(null)

    useEffect(() => {
        if (props.upload_id)
            fetchEntityOverlaps(props.upload_id)
    }, [props.upload_id])


    const fetchEntityOverlaps = (upload_id: number) => {
        setLoading(true)
        axios.get(`${FETCH_ENTITY_OVERLAPS_URL}${upload_id}/`).then(
          response => {
            setLoading(false)
            setData(response.data as OverlapItemInterface[])
          }, error => {
            setLoading(false)
            console.log(error)
          }
        )
    }
    

    const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
        setSelectedEntityIds({
            'entityId1': parseInt(rowData[1]),
            'entityId2': parseInt(rowData[4])
        })
    }

    return (
        <Grid container flexDirection={'column'} sx={{height: '100%'}}>
            <Grid item>
                <h2>Overlaps Error</h2>
            </Grid>
            <Grid item flexDirection={'column'} flex={1} flexBasis={`${MIN_HEIGHT}px`}>
                <Grid container flexDirection={'row'} sx={{height: '100%'}}>
                    <Grid item flex={2} sx={{display:'flex'}}>
                        { loading ? 
                            <div style={{ width: '100%' }}>
                                <Grid container flexDirection={'column'} alignItems={'center'} spacing={1}>
                                    <Grid item>
                                        <Loading/>
                                    </Grid>
                                    <Grid item>
                                        { 'Retrieving data...' }                
                                    </Grid>
                                </Grid>
                            </div> :
                            <List
                                pageName={''}
                                listUrl={''}
                                initData={data as RowData[]}
                                isRowSelectable={false}
                                selectionChanged={null}
                                editUrl={''}
                                onRowClick={handleRowClick}
                                excludedColumns={['id_1', 'id_2']}
                            />
                        }
                        
                    </Grid>
                    <Grid item flex={1}>
                        <OverlapsErrorMap entityIds={selectedEntityIds}  />
                    </Grid>
                </Grid>
            </Grid>
            <Grid item>
                <Button variant={'contained'} onClick={() => props.onBackClicked()}>
                    Back
                </Button>
            </Grid>
        </Grid>
    )
}

import React, {useEffect, useRef, useState, useCallback} from 'react';
import ReactDOM from "react-dom/client";
import axios from "axios";
import maplibregl, {AttributionControl, IControl, Marker} from 'maplibre-gl';
import {
    Skeleton,
    Switch,
    FormLabel,
    FormControlLabel,
    FormControl,
    Card,
    CardContent,
    Box,
    Typography,
    Stack,
    Chip,
    Snackbar,
    Alert
} from '@mui/material';
import Divider from '@mui/material/Divider';
import { usePrevious } from '../../utils/Helpers';

const MAP_STYLE_URL = window.location.origin + '/api/dataset-style/dataset/'
const VIEW_MAP_STYLE_URL = window.location.origin + '/api/dataset-style/view/'
const HIGHLIGHT_COLOR = '#32cd32'
const MAX_FILTER_BY_POINT = 10

export interface EntityItemInterface {
    id: number,
    level: number,
    centroid?: any
}

export interface EntitiesMapInterface {
    dataset_id: string,
    datasetUuid: string,
    styleSourceName: string,
    session: string,
    filter_changed: Date,
    bbox?: any,
    selectedGeom?: any,
    selectedEntityOnHover?: EntityItemInterface,
    initialMarkers?: any[],
    entityOnMapHover?: (item: EntityItemInterface) => void,
    addFilterByPoints?: (points: any[]) => void,
    datasetViewUuid?: string
}

interface LMarker extends Marker {
    label: string
}

function ToggleSelect(props: any) {
    const [checked, setChecked] = useState(false)
    const [zoomHandler, setZoomHandler] = useState(false)
    const [zoom, setZoom] = useState(props.map ? props.map.getZoom().toFixed(2) : 0)

    useEffect(()=> {
        if (!props.map) return;
        if (checked) {
            // disable map zoom when using select
            props.map.scrollZoom.disable()
        } else {
            props.map.scrollZoom.enable()
        }
    }, [checked])

    useEffect(() => {
        if (props.map && !zoomHandler) {
            setZoomHandler(true)
            props.map.on('zoom', () => {
                setZoom(props.map.getZoom().toFixed(2))
            })
        }
    }, [props.map])

    const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setChecked(event.target.checked)
        if (props.onToggleSelect)
            props.onToggleSelect(event.target.checked)
    }
    
    return (
        <Card sx={{ display: 'flex' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flex: '1 0 auto', padding: '5px !important' }}>
                    <FormControl component="fieldset" variant="standard">
                        <Stack direction="column" spacing={0}>
                            <Box>
                                <Typography>Zoom: {zoom}</Typography>
                            </Box>
                            <Divider orientation='horizontal' style={{width:'100%'}} />
                            <Stack direction="row" spacing={1} alignItems="center">
                                <FormControlLabel label="Select to Filter"
                                control={<Switch checked={checked} onChange={handleChange} />}  />
                            </Stack>
                        </Stack>                        
                    </FormControl>
                </CardContent>
            </Box>
        </Card>
    )
}

class SelectControl<IControl> {
    private _container: any;
    private _map: any;
    private _selectMode: boolean;

    constructor() {
        this._selectMode = false;
    }

    isSelectMode() {
        return this._selectMode;
    }

    onAdd(map: any){
        this._map = map;
        this._container = document.createElement('div');
        this._container.className = 'maplibregl-ctrl';
        const toogle_select = (value: boolean) => {
            this._selectMode = value
        }
        const divRoot = ReactDOM.createRoot(this._container)
        let _preferences: any = window.preferences
        let _maptiler = _preferences ? _preferences['maptiler_api_key'] : ''
        divRoot.render(
          <>
              {_maptiler ? null : <h2>Please set Maptiler API Key on the admin!</h2>}
              <ToggleSelect map={this._map} onToggleSelect={toogle_select} />
          </>
        );
        return this._container;
    }

    onRemove() {
        this._container.parentNode.removeChild(this._container)
        this._map = undefined
    }
}

export default function EntitiesMap(props: EntitiesMapInterface) {
    const mapContainer = useRef(null);
    const map = useRef(null);
    const mapToggleRef = useRef(null);
    const [lng] = useState(139.753);
    const [lat] = useState(35.6844);
    const [zoom] = useState(1);
    const [loading, setLoading] = useState(true)
    const [geomAdded, setGeomAdded] = useState<boolean>(false)
    const [mapLoaded, setMapLoaded] = useState<boolean>(false)
    const [tilesLoaded, setTilesLoaded] = useState<boolean>(false)
    const [levelCount, setLevelCount] = useState<number>(4)
    const [geomOnHoverAdded, setGeomOnHoverAdded] = useState<boolean>(false)
    const prevSelectedEntityOnHover = usePrevious(props.selectedEntityOnHover)
    const [markers, setMarkers] = useState<LMarker[]>([])
    const mapMarkersRef = useRef(markers)
    const [mapMarkersInit, setMapMarkersInit] = useState(false)
    const [showErrorMessage, setShowErrorMessage] = useState(false)
    const [errorMessage, setErrorMessage] = useState<string>("")

    function updateMapMarkers(newMarkers: any) {
        mapMarkersRef.current = newMarkers
        setMarkers(newMarkers)
        if (props.addFilterByPoints) {
            props.addFilterByPoints(newMarkers.map((marker: LMarker) => [marker.getLngLat().wrap().lng, marker.getLngLat().wrap().lat, marker.label]))
        }
    }

    const getMapStyleURL = () => {
        let _map_style_url = MAP_STYLE_URL + `${props.datasetUuid}/?session=${props.session}`
        if (props.datasetViewUuid) {
            _map_style_url = VIEW_MAP_STYLE_URL + `${props.datasetViewUuid}/?session=${props.session}`
        }
        return _map_style_url
    }

    useEffect(() => {
        if (!loading) {
            if (map.current) return; //stops map from intializing more than once
            map.current = new maplibregl.Map({
                container: mapContainer.current,
                style: getMapStyleURL(),
                center: [lng, lat],
                zoom: zoom,
                attributionControl: false
            })
            map.current.addControl(new AttributionControl(), 'top-left')
            map.current.on('load', () => {
                setMapLoaded(true)
            })
            map.current.on('click', mapOnClick)
            mapToggleRef.current = new SelectControl()
            map.current.addControl(mapToggleRef.current, 'top-right')
        }
    }, [loading])

    useEffect(() => {
        if (props.bbox && map.current) {
            map.current.fitBounds(props.bbox, {
                padding: 30
            })
        }
    }, [props.bbox])

    useEffect(() => {
        if (!map.current) return;
        if (!tilesLoaded)return;
        // Draw main boundary
        if (props.selectedGeom) {
            if (geomAdded) {
                map.current.removeLayer('selectedGeom')
                map.current.removeSource('selectedGeom')
            }
             map.current.addSource('selectedGeom', {
                'type': 'geojson',
                'data': props.selectedGeom
            })
            setGeomAdded(true)
            map.current.addLayer({
                'id': 'selectedGeom',
                'type': 'line',
                'source': 'selectedGeom',
                'layout': {},
                'paint': {
                    'line-color': HIGHLIGHT_COLOR,
                    'line-width': 4
                }
            });
        } else {
            if (geomAdded) {
                map.current.removeLayer('selectedGeom')
                map.current.removeSource('selectedGeom')
                setGeomAdded(false)
            }
        }
    }, [props.selectedGeom])

    useEffect(() => {
        if (!map.current) return;
        if (!tilesLoaded)return;
        // Draw main boundary
        if (props.selectedEntityOnHover.id) {
            if (geomOnHoverAdded && prevSelectedEntityOnHover.id) {
                map.current.setFeatureState(
                    { 
                        source: props.styleSourceName,
                        id: prevSelectedEntityOnHover.id,
                        sourceLayer: `level_${prevSelectedEntityOnHover.level}`
                    },
                    { hover: false }
                )
                setGeomOnHoverAdded(false)
            }
            map.current.setFeatureState(
                { 
                    source: props.styleSourceName,
                    id: props.selectedEntityOnHover.id,
                    sourceLayer: `level_${props.selectedEntityOnHover.level}`
                },
                { hover: true }
            )
            setGeomOnHoverAdded(true)
        } else {
            if (geomOnHoverAdded && prevSelectedEntityOnHover.id) {
                map.current.setFeatureState(
                    { 
                        source: props.styleSourceName,
                        id: prevSelectedEntityOnHover.id,
                        sourceLayer: `level_${prevSelectedEntityOnHover.level}`
                    },
                    { hover: false }
                )
                setGeomOnHoverAdded(false)
            }
        }
    }, [props.selectedEntityOnHover.id])
    

    useEffect(() => {
        setTimeout(() => {
            setLoading(false)
        }, 200)
    }, [])

    useEffect(() => {
        if (!mapLoaded) return;
        if (props.filter_changed) {
            initMapMarker()
        }
        setTilesLoaded(true)
    }, [mapLoaded])

    useEffect(() => {
        // when there is filter changed, then redraw tiles
        if (map.current && mapLoaded) {
            setTilesLoaded(false)
            map.current.setStyle(getMapStyleURL())
            setGeomAdded(false)
            setTilesLoaded(true)
        }

        // resize map to make it larger when filter is removed
        if (map.current) {
            map.current.resize()
        }
        if (props.filter_changed && !mapMarkersInit) {
            // init map markers for the first time
            initMapMarker()
        }
        if (props.filter_changed && mapMarkersInit && props.initialMarkers) {
            if (markers.length != props.initialMarkers.length) {
                // if marker is removed from filter chips, then redraw map marker
                redrawMapMarker()
            }
        }
    }, [props.filter_changed])

    useEffect(() => {
        if (!map.current) return;
        if (!mapLoaded) return;
        if (!props.datasetUuid && !props.datasetViewUuid) return;
        let _url = ''
        if (props.datasetUuid) {
            _url = `/api/map/dataset/${props.datasetUuid}/bbox/`
        } else if (props.datasetViewUuid) {
            _url = `/api/map/view/${props.datasetViewUuid}/bbox/`
        }
        if (!_url) return;
        axios.get(_url).then(
            response => {
                if (response.data && response.data.length === 4) {
                    map.current.fitBounds(response.data, {
                        padding: 30
                    })
                }
            }
        )
    }, [mapLoaded, props.datasetUuid, props.datasetViewUuid])
    
    const drawMarker = (label: any, lngLat: any):LMarker => {
        let container = document.createElement('div')
        const divRoot = ReactDOM.createRoot(container)
        divRoot.render(<Chip label={label} color="primary" />)
        var marker:LMarker = new maplibregl.Marker(container)
                    .setLngLat(lngLat)
                    .addTo(map.current) as LMarker
        marker.label = label
        return marker
    }

    const mapOnClick = (e: any) => {
        if (mapToggleRef.current.isSelectMode()) {
            if (mapMarkersRef.current.length < MAX_FILTER_BY_POINT) {
                let lastIdx = mapMarkersRef.current.length ? mapMarkersRef.current[mapMarkersRef.current.length-1].label : '0'
                let label = parseInt(lastIdx)+1
                var marker = drawMarker(label.toString(), e.lngLat) as LMarker
                updateMapMarkers([...mapMarkersRef.current, marker])
            } else {
                setErrorMessage(`Cannot add marker more than ${MAX_FILTER_BY_POINT}!`)
                setShowErrorMessage(true)
            }
        }
    }

    const initMapMarker = () => {
        if (!map.current) return;
        if (!mapLoaded) return;
        if (mapMarkersInit) return;
        let new_markers:LMarker[] = []
        if (props.initialMarkers) {
            for (let mPoint of props.initialMarkers) {
                var marker = drawMarker(mPoint[2], [mPoint[0], mPoint[1]]) as LMarker
                new_markers.push(marker)
            }
        }
        setMarkers(new_markers)
        mapMarkersRef.current = new_markers
        setMapMarkersInit(true)
    }

    const redrawMapMarker = () => {
        if (!map.current) return;
        if (!mapLoaded) return;
        for (let mMarker of mapMarkersRef.current) {
            mMarker.remove()
        }
        let new_markers:LMarker[] = []
        if (props.initialMarkers) {
            for (let mPoint of props.initialMarkers) {
                var marker = drawMarker(mPoint[2], [mPoint[0], mPoint[1]]) as LMarker
                new_markers.push(marker)
            }
        }
        setMarkers(new_markers)
        mapMarkersRef.current = new_markers
    }

    return (
    <div className='map-wrap'>
        { loading ?
            <Skeleton variant='rectangular' height={'100%'} width={'100%'}/> :
            <div ref={mapContainer} className='map' />}
        
        <Snackbar open={showErrorMessage} autoHideDuration={6000}
            anchorOrigin={{vertical:'top', horizontal:'center'}}
            onClose={()=>setShowErrorMessage(false)}>
            <Alert onClose={()=>setShowErrorMessage(false)} severity="error" sx={{ width: '100%' }}>
            {errorMessage}
            </Alert>
        </Snackbar>
    </div>
    )
}
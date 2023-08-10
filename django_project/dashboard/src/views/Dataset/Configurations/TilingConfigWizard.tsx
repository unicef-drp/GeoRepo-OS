import React, {useEffect, useState, useRef} from 'react';
import ReactDOM from "react-dom/client";
import {useNavigate, useSearchParams} from "react-router-dom";
import axios from "axios";
import toLower from "lodash/toLower";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import Skeleton from '@mui/material/Skeleton';
import maplibregl, {AttributionControl} from "maplibre-gl";
import AlertMessage from '../../../components/AlertMessage';
import {postData} from "../../../utils/Requests";
import TabPanel, {a11yProps} from '../../../components/TabPanel';
import {DatasetTilingConfigMatrix, TilingConfig} from './DatasetTilingConfig';
import Scrollable from '../../../components/Scrollable';
import {useAppDispatch} from "../../../app/hooks";
import {updateMenu} from "../../../reducers/breadcrumbMenu";


interface TabInterface {
    onNext?: () => void,
    onBack?: () => void
}

const FETCH_DATASET_DETAIL_URL = '/api/dataset-detail/'
const FETCH_VIEW_DETAIL_URL = '/api/view-detail/'
const TILING_CONFIGS_TEMP_DETAIL_URL = '/api/tiling-configs/temporary/detail/'
const TILING_CONFIGS_TEMP_CONFIRM_URL = '/api/tiling-configs/temporary/apply/'
const TILING_CONFIGS_STATUS_URL = '/api/tiling-configs/status/'
const WINDOW_PREFERENCES: any = window.preferences
const MAPTILER_API_KEY = WINDOW_PREFERENCES ? WINDOW_PREFERENCES['maptiler_api_key'] : ''
const MAP_STYLE_ORIGINAL_URL = `https://api.maptiler.com/maps/streets/style.json?key=${MAPTILER_API_KEY}`

const HIGHLIGHT_COLOR = '#32cd32'
const VECTOR_LINE_COLORS = [
    '#FF69B4',
    '#37f009',
    '#096FF0',
    '#d9f009',
    '#fa02cd',
    '#fa5d02',
    '#fc5e63'
]

function ZoomInfo(props: any) {
    const [zoomHandler, setZoomHandler] = useState(false)
    const [zoom, setZoom] = useState(props.map ? props.map.getZoom().toFixed(2) : 0)

    useEffect(() => {
        if (props.map && !zoomHandler) {
            setZoomHandler(true)
            props.map.on('zoom', () => {
                setZoom(props.map.getZoom().toFixed(2))
            })
        }
    }, [props.map])

    
    return (
        <Card sx={{ display: 'flex' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flex: '1 0 auto', padding: '10px !important' }}>
                    <FormControl component="fieldset" variant="standard">
                        <Stack direction="column" spacing={0}>
                            <Box>
                                <Typography>Zoom: {zoom}</Typography>
                            </Box>
                            <Divider orientation='horizontal' style={{width:'100%'}} />
                            <Stack direction="row" spacing={1} alignItems="center">
                            </Stack>
                        </Stack>                        
                    </FormControl>
                </CardContent>
            </Box>
        </Card>
    )
}

class MapControl<IControl> {
    private _container: any;
    private _map: any;

    constructor() {
    }

    onAdd(map: any){
        this._map = map;
        this._container = document.createElement('div');
        this._container.className = 'maplibregl-ctrl';
        const divRoot = ReactDOM.createRoot(this._container)
        divRoot.render(<ZoomInfo map={this._map} />);
        return this._container;
    }

    onRemove() {
        this._container.parentNode.removeChild(this._container)
        this._map = undefined
    }
}

function TilingConfigPreview(props: any) {
    const mapContainer = useRef(null);
    const map = useRef(null);
    const mapControlRef = useRef(null);
    const [lng] = useState(139.753);
    const [lat] = useState(35.6844);
    const [zoom] = useState(1);
    const [bbox, setBbox] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [mapLoaded, setMapLoaded] = useState(false)
    const [minZoom, setMinZoom] = useState(0);
    const [maxZoom, setMaxZoom] = useState(8);

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

    const addMapLayers = () => {
        let _url = window.location.origin
        if (props.viewUUID) {
            _url = _url + `/api/dashboard-tiles/maps/tile-preview/view/${props.viewUUID}/${props.session}/{z}/{x}/{y}/`
        } else if (props.datasetUUID) {
            _url = _url + `/api/dashboard-tiles/maps/tile-preview/dataset/${props.datasetUUID}/${props.session}/{z}/{x}/{y}/`
        }
        if (_url === '') return;
        map.current.addSource('tiling_preview', {
            'type': 'vector',
            'tiles': [_url],
            'tolerance': 0,
            'maxzoom': maxZoom,
            'minzoom': minZoom
        })
        for (let _level=0; _level < VECTOR_LINE_COLORS.length; ++_level) {
            map.current.addLayer({
                'id': `level_${_level}`,
                'source': 'tiling_preview',
                'source-layer': `level_${_level}`,
                'type': 'line',
                'paint': {
                    'line-color': [
                        'case',
                        ['boolean', ['feature-state', 'hover'], false],
                        HIGHLIGHT_COLOR,
                        VECTOR_LINE_COLORS[_level % VECTOR_LINE_COLORS.length]
                    ],
                    'line-width': [
                        'case',
                        ['boolean', ['feature-state', 'hover'], false],
                        4,
                        1
                    ]
                }
            })
        }
    }

    useEffect(() => {
        let _fetch_url = `${TILING_CONFIGS_TEMP_DETAIL_URL}${props.session}/`
        axios.get(_fetch_url).then(
            response => {
                let _data = response.data as TilingConfig[]
                if (_data && _data.length) {
                    setMinZoom(_data[0].zoom_level)
                    setMaxZoom(_data[_data.length-1].zoom_level)
                }
                setLoading(false)
            }
        )
    }, []);

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
                addMapLayers()
                mapFitBounds()
            })
            mapControlRef.current = new MapControl()
            map.current.addControl(mapControlRef.current, 'top-right')
        }
    }, [loading])

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
                <div className='map-wrap'>
                    { loading ?
                        <Skeleton variant='rectangular' height={'100%'} width={'100%'}/> :
                        <div ref={mapContainer} className='map' />
                    }
                </div>
            </div>
            <div className="button-container" style={{marginLeft:0, width: '100%', padding: '10px'}}>
                <Grid container direction='row' justifyContent='space-between' sx={{paddingRight: '20px'}}>
                    <Grid item>
                        <Button disabled={loading} onClick={() => props.onBackClicked()} variant="outlined">
                            Back
                        </Button>
                    </Grid>
                    <Grid item>
                        <Button disabled={loading} onClick={() => props.onNextClicked()} variant="contained">
                            Next
                        </Button>
                    </Grid>
                </Grid>
            </div>
        </div>
    )
}

function TilingConfigConfirm(props: any) {
    const [loading, setLoading] = useState(false)

    const confirmTilingConfig = () => {
        setLoading(true)
        let _data = {
            'object_uuid': props.viewUUID ? props.viewUUID : props.datasetUUID,
            'object_type': props.viewUUID ? 'datasetview' : 'dataset',
            'session': props.session
        }
        postData(TILING_CONFIGS_TEMP_CONFIRM_URL, _data).then(
            response => {
                setLoading(false)
                props.onTilingConfigConfirmed()
            }
        ).catch(error => {
            setLoading(false)
            console.log('error ', error)
            alert('Error saving tiling config...')
        })
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'auto' }}>
            <Grid container>
                <Grid item>
                    <Typography>Please check and confirm the configuration:</Typography>
                </Grid>
                <Grid item>
                    <DatasetTilingConfigMatrix session={props.session} isReadOnly={true} hideActions={true}/>
                </Grid>
                <Grid item sx={{marginLeft:0, width: '100%', padding: '10px'}}>
                    <Grid container direction='row' justifyContent='space-between'>
                        <Grid item>
                        </Grid>
                        <Grid item>
                            <Button disabled={loading} onClick={() => confirmTilingConfig()} variant="contained">
                                Confirm and Save
                            </Button>
                        </Grid>
                    </Grid>
                </Grid>
            </Grid>
        </Box>
    )
}


export default function TilingConfigWizard(props: any) {
    // Tab 1: Tiling Config editable
    // Tab 2: Preview
    // Tab 3: Confirm+Save + Progress
    const [tabSelected, setTabSelected] = useState(0)
    const [searchParams, setSearchParams] = useSearchParams()
    const [session, setSession] = useState(null)
    const [datasetUUID, setDatasetUUID] = useState(null)
    const [viewUUID, setViewUUID] = useState(null)
    const [alertMessage, setAlertMessage] = useState<string>('')
    const navigate = useNavigate()
    const dispatch = useAppDispatch();

    useEffect(() => {
        let _view_uuid = searchParams.get('view_uuid')
        let _dataset_uuid = searchParams.get('dataset_uuid')
        let _url = _view_uuid ? `${FETCH_VIEW_DETAIL_URL}${_view_uuid}` : `${FETCH_DATASET_DETAIL_URL}${_dataset_uuid}/`
        axios.get(`${_url}`).then((response) => {
            let _session = searchParams.get('session')
            setSession(_session)
            setViewUUID(_view_uuid)
            setDatasetUUID(_dataset_uuid)
            if (_view_uuid) {
                // append view name to View Breadcrumbs
                let _name = response.data.name
                dispatch(updateMenu({
                    id: `view_edit`,
                    name: _name,
                    link: `/view_edit?id=${response.data.id}`
                }))
            } else {
                // append dataset name to Dataset Breadcrumbs
                let _name = response.data.dataset
                if (response.data.type) {
                    _name = _name + ` (${response.data.type})`
                }
                let moduleName = toLower(response.data.type.replace(' ', '_'))
                dispatch(updateMenu({
                    id: `${moduleName}_dataset_entities`,
                    name: _name,
                    link: `/${moduleName}/dataset_entities?id=${response.data.id}`
                }))
            }
        }).catch((error) => {
            console.log('Error fetching dataset detail ', error)
        })
    }, [searchParams])

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        setTabSelected(newValue)
    }

    const onTilingConfigUpdated = () => {
        setTabSelected(1)
    }

    const onBack = () => {
        setTabSelected(tabSelected - 1)
    }

    const onNext = () => {
        setTabSelected(tabSelected + 1)
    }

    const onTilingConfigConfirmed = () => {
        // display message, then navigate to dataset/view tiling config tab
        setAlertMessage('Successfully updating tiling config! Simplification and vector tiles generation will be run in the background.')
    }

    const onRedirectToTilingConfig = () => {
        let _object_type = viewUUID ? 'datasetview' : 'dataset'
        let _object_uuid = viewUUID ? viewUUID : datasetUUID 
        let _fetch_url = `${TILING_CONFIGS_STATUS_URL}${_object_type}/${_object_uuid}/`
        axios.get(_fetch_url).then(
            response => {
                setAlertMessage('')
                let moduleName = toLower(response.data['module']).replace(' ', '_')
                let _path = ''
                let _object_id = response.data['object_id']
                if (viewUUID) {
                    _path = `/view_edit?id=${_object_id}&tab=3`
                } else {
                    _path = `/${moduleName}/dataset_entities?id=${_object_id}&tab=5`
                }
                navigate(_path)
            }
        )
    }

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <AlertMessage message={alertMessage} onClose={() => onRedirectToTilingConfig()} />
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabSelected} onChange={handleChange} aria-label="Tiling Config Tab">
                    <Tab label="1 - Detail" {...a11yProps(0)} />
                    <Tab label="2 - Preview" {...a11yProps(1)} disabled={tabSelected < 1} />
                    <Tab label="3 - Confirm" {...a11yProps(2)} disabled={tabSelected < 2} />
                </Tabs>
            </Box>
            {session && (
                <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                    <TabPanel value={tabSelected} index={0}>
                        <Scrollable>
                            <DatasetTilingConfigMatrix session={session} isReadOnly={false} onTilingConfigUpdated={onTilingConfigUpdated} hideBottomNotes={true} />
                        </Scrollable>
                    </TabPanel>
                    <TabPanel value={tabSelected} index={1} noPadding>
                        <Scrollable>
                            <TilingConfigPreview session={session} viewUUID={viewUUID} datasetUUID={datasetUUID} onBackClicked={onBack} onNextClicked={onNext} />
                        </Scrollable>
                    </TabPanel>
                    <TabPanel value={tabSelected} index={2}>
                        <Scrollable>
                            <TilingConfigConfirm session={session} viewUUID={viewUUID} datasetUUID={datasetUUID} onBack={onBack} onTilingConfigConfirmed={onTilingConfigConfirmed} />
                        </Scrollable>
                    </TabPanel>
                </Grid>
            )}
        </div>
    )
}
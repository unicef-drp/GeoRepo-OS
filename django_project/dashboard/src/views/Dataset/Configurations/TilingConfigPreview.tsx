import React, {useEffect, useState, useRef, ChangeEvent} from 'react';
import ReactDOM from "react-dom/client";
import axios from "axios";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import Skeleton from '@mui/material/Skeleton';
import maplibregl, {AttributionControl} from "maplibre-gl";
import {TilingConfig} from './DatasetTilingConfig';

const TILING_CONFIGS_TEMP_DETAIL_URL = '/api/tiling-configs/temporary/detail/'
const WINDOW_PREFERENCES: any = window.preferences
const MAPTILER_API_KEY = WINDOW_PREFERENCES ? WINDOW_PREFERENCES['maptiler_api_key'] : ''
const MAP_STYLE_ORIGINAL_URL = `https://api.maptiler.com/maps/streets/style.json?key=${MAPTILER_API_KEY}`
const mapshaper = (window as any).mapshaper;
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

interface AdminLevelSimplifyFactor {
    zoomLevel: number;
    simplify: number;
}

interface GeoJSONFile {
    file: File;
    level: number;
    factors: AdminLevelSimplifyFactor[];
}

export default function TilingConfigPreview(props: any) {
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

        // let _url = window.location.origin
        // if (props.viewUUID) {
        //     _url = _url + `/api/dashboard-tiles/maps/tile-preview/view/${props.viewUUID}/${props.session}/{z}/{x}/{y}/`
        // } else if (props.datasetUUID) {
        //     _url = _url + `/api/dashboard-tiles/maps/tile-preview/dataset/${props.datasetUUID}/${props.session}/{z}/{x}/{y}/`
        // }
        // if (_url === '') return;
        // map.current.addSource('tiling_preview', {
        //     'type': 'vector',
        //     'tiles': [_url],
        //     'tolerance': 0,
        //     'maxzoom': maxZoom,
        //     'minzoom': minZoom
        // })
        // for (let _level=0; _level < VECTOR_LINE_COLORS.length; ++_level) {
        //     map.current.addLayer({
        //         'id': `level_${_level}`,
        //         'source': 'tiling_preview',
        //         'source-layer': `level_${_level}`,
        //         'type': 'line',
        //         'paint': {
        //             'line-color': [
        //                 'case',
        //                 ['boolean', ['feature-state', 'hover'], false],
        //                 HIGHLIGHT_COLOR,
        //                 VECTOR_LINE_COLORS[_level % VECTOR_LINE_COLORS.length]
        //             ],
        //             'line-width': [
        //                 'case',
        //                 ['boolean', ['feature-state', 'hover'], false],
        //                 4,
        //                 1
        //             ]
        //         }
        //     })
        // }
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

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const file = e.target.files[0]
            const reader = new FileReader()
            reader.onload = function (theFile: any) {
                var data = {
                    content: theFile.target.result,
                    filename: theFile.target.fileName
                }
                var dataset = mapshaper.internal.importContent({
                    json: data
                }, {})
                var simplifyOpts = {
                    method: 'dp',
                    percentage: 0.05,
                    no_repair: true,
                    keep_shapes: true,
                    planar: false
                }
                mapshaper.cmd.simplify(dataset, simplifyOpts);
                console.log(dataset)
                var output = mapshaper.internal.exportFileContent(dataset, {
                    format: 'geojson',
                    gj2008: true
                })
                console.log(output)
                map.current.addSource('uploaded-source', {
                    'type': 'geojson',
                    'data': JSON.parse(output[0].content)
                });
    
                map.current.addLayer({
                    'id': 'uploaded-polygons',
                    'type': 'line',
                    'source': 'uploaded-source',
                    "paint": {
                        "line-color": "#32cd32",
                        "line-width": 1
                    }
                });
            };
    
            // Read the GeoJSON as text
            reader.readAsArrayBuffer(file);
        }
      }

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
                        <input
                            type="file"
                            id="file"
                            name="file"
                            accept="application/geo+json,application/vnd.geo+json,.geojson"
                            onChange={handleFileChange}
                        />
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
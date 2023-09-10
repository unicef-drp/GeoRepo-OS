import React, {useEffect, useState, useRef, ChangeEvent, createRef, useCallback} from 'react';
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
import maplibregl, {AttributionControl} from "maplibre-gl";
import IconButton from '@mui/material/IconButton';
import DoDisturbOnIcon from '@mui/icons-material/DoDisturbOn';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteIcon from '@mui/icons-material/Delete';
import { TextField } from '@mui/material';
import { usePrevious } from '../../../utils/Helpers';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import {postData} from "../../../utils/Requests";
import { TilingConfig } from './DatasetTilingConfig';

const TILING_CONFIGS_TEMP_DETAIL_URL = '/api/tiling-configs/temporary/preview/'
const TILING_CONFIGS_TEMP_SAVE_URL = '/api/tiling-configs/temporary/detail/'
const PREVIEW_GEOJSON_URL = '/api/tiling-configs/temporary/geojson/'
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
    '#fc5e63',
    '#fc5e63',
    '#fc5e63'
]


interface AdminLevelSimplification {
    level: number;
    simplify: number;
    isIncluded: boolean;
    isHidden: boolean;
}

interface AdminLevelSimplifyItemInterface {
    item: AdminLevelSimplification;
    onValueUpdated: (adminLevel: number, value: number) => void,
    onValueRemoved: (adminLevel: number) => void,
}

function AdminLevelSimplifyItem(props: AdminLevelSimplifyItemInterface) {
    const [isHovering, setIsHovering] = useState(false)
    const [isEdit, setIsEdit] = useState(false)
    const [idx, setIdx] = useState(-1)
    const [simplify, setSimplify] = useState(props.item.isIncluded ? props.item.simplify : 1)

    useEffect(() => {
        let _idx = props.item.isIncluded ? 0 : -1
        setIdx(_idx)
        setSimplify(props.item.isIncluded ? props.item.simplify : 1)
    }, [props.item])

    const handleMouseOver = () => {
        setIsHovering(true)
    }

    const handleMouseOut = () => {
        setIsHovering(false)
    }

    const rightButtonOnClick = () => {
        if (idx === -1) {
            setIsEdit(true)
        } else {
            props.onValueRemoved(props.item.level)
        }
    }

    const onKeyPress = (e: any) => {
        if(e.keyCode == 13){
            e.preventDefault()
            setIsEdit(false)
            props.onValueUpdated(props.item.level, simplify)
        } else if (e.keyCode == 27) {
            // reset value
            e.preventDefault()
            setIsEdit(false)
            setSimplify(props.item.isIncluded ? props.item.simplify : 1)
        }
    }

    const onChange = (e: any) => {
        setSimplify(parseFloat(e.target.value))
    }

    return (
        <Box>
            { !isEdit && (
                <Grid container flexDirection={'row'} alignItems={'center'} justifyContent={'center'}
                    onMouseOver={handleMouseOver}
                    onMouseOut={handleMouseOut}>
                    <Grid item sx={{minWidth: '64px'}}>
                        { idx === -1 ? (
                            <IconButton><DoDisturbOnIcon color='error' fontSize='small' /></IconButton>
                        ) : (
                            <Button size='small' sx={{width:'40px'}}
                                onClick={()=>setIsEdit(true)}>
                                {simplify}
                            </Button>
                        )}
                    </Grid>
                    <Grid item>
                        <IconButton aria-label="delete" sx={{visibility: isHovering?'visible':'hidden'}} onClick={rightButtonOnClick}>
                            { idx !== -1 ? (
                                <DeleteIcon fontSize='small' />
                            ) : (
                                <AddCircleOutlineIcon fontSize='small' />
                            )}
                        </IconButton>
                    </Grid>
                </Grid>
            )}
            {isEdit && (
                <Grid container flexDirection={'row'} alignItems={'center'} justifyContent={'center'}>
                    <Grid item className='InputHideArrows'>
                        <TextField
                            id="outlined-number"
                            label="Tolerance"
                            type="number"
                            InputLabelProps={{
                                shrink: true,
                            }}
                            size="small"
                            sx={{
                                width: '100px'
                            }}
                            value={simplify}
                            onChange={onChange}
                            onKeyDown={onKeyPress}
                            autoFocus
                        />
                    </Grid>
                </Grid>
            )}
        </Box>
    )
}


function ZoomInfo(props: any) {
    const [zoomHandler, setZoomHandler] = useState(false)
    const [zoom, setZoom] = useState(props.map ? props.map.getZoom().toFixed(2) : 0)
    const [items, setItems] = useState<AdminLevelSimplification[]>([])

    useEffect(() => {
        if (props.map && !zoomHandler) {
            setZoomHandler(true)
            props.map.on('zoom', () => {
                setZoom(props.map.getZoom().toFixed(2))
            })
        }
    }, [props.map])

    useEffect(() => {
        if (!props.data) return;
        let _items: AdminLevelSimplification[] = []
        // Iterate from 0 - 6 admin levels
        for (let i = 0; i < 7; ++i) {
            let _idx = props.data.findIndex((item: any) => item.level === i)
            if (_idx > -1) {
                _items.push({
                    level: i,
                    simplify: props.data[_idx].simplify,
                    isIncluded: props.data[_idx].isIncluded,
                    isHidden: props.data[_idx].isHidden
                })
            } else {
                _items.push({
                    level: i,
                    simplify: 1,
                    isIncluded: false,
                    isHidden: false
                })
            }
        }
        setItems(_items)
    }, [props.data])

    const onValuRemoved = (adminLevel: number) => {
        let _items = items.map((item) => {
            if (item.level === adminLevel) {
                item.isIncluded = false
            }
            return {...item}
        })
        setItems(_items)
    }

    const onValueUpdated = (adminLevel: number, simplify: number) => {
        let _items = items.map((item) => {
            if (item.level === adminLevel) {
                item.simplify = simplify
                item.isIncluded = true
            }
            return  {...item}
        })
        setItems(_items)
    }

    const onSubmit = () =>{
        if (props.onApplyAtZoomLevel) {
            props.onApplyAtZoomLevel(zoom, items)
        }
    }

    const toggleVisibilityLayer = (adminLevel: number) => {
        if (props.toggleVisibilityLayer) {
            props.toggleVisibilityLayer(adminLevel)
        }
    }
    
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
                            { items.map((item) => {
                                return (
                                    <Stack key={item.level} direction="row" spacing={1} alignItems="center">
                                        <Box>
                                            <IconButton aria-label="visibility" onClick={() => toggleVisibilityLayer(item.level)}>
                                                { item.isHidden ? (
                                                    <VisibilityOffIcon fontSize='small' />
                                                ) : (
                                                    <VisibilityIcon fontSize='small' />
                                                )}
                                            </IconButton>
                                        </Box>
                                        <Box>
                                            <Typography>Admin Level {item.level}: </Typography>
                                        </Box>
                                        <Box>
                                            <AdminLevelSimplifyItem item={item} onValueRemoved={onValuRemoved} onValueUpdated={onValueUpdated} />
                                        </Box>
                                    </Stack>
                                )
                            })
                            }
                            <Stack direction="row" spacing={1} alignItems="center" marginLeft={'auto'} marginRight={'auto'} padding={0.5}>
                                <Box className="button-container">
                                    <Button onClick={onSubmit} variant="contained">Apply</Button>
                                </Box>
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
    private _divRoot: any;
    private _toggleVisibilityLayer: any;
    private _onApplyAtZoomLevel: any;

    constructor(toggleVisibilityLayer: any, onApplyAtZoomLevel: any) {
        this._toggleVisibilityLayer = toggleVisibilityLayer
        this._onApplyAtZoomLevel = onApplyAtZoomLevel
    }

    onAdd(map: any){
        this._map = map;
        this._container = document.createElement('div');
        this._container.className = 'maplibregl-ctrl';
        this._divRoot = ReactDOM.createRoot(this._container)
        this._divRoot.render(<ZoomInfo map={this._map} />);
        return this._container;
    }

    onRemove() {
        this._container.parentNode.removeChild(this._container)
        this._map = undefined
    }

    setData(items: GeoJSONFileMeta[], toggleVisibilityLayer: any, onApplyAtZoomLevel: any) {
        if (!this._map) return
        this._toggleVisibilityLayer = toggleVisibilityLayer
        this._onApplyAtZoomLevel = onApplyAtZoomLevel
        let _items: AdminLevelSimplification[] = []
        let _currentZoom = Math.trunc(this._map.getZoom())
        for (let i = 0; i < items.length; ++i) {
            let _item = items[i]
            let _idx = _item.factors.findIndex((factor) => factor.zoom_level === _currentZoom)
            if (_idx > -1) {
                _items.push({
                    level: _item.level,
                    simplify: _item.factors[_idx].simplify,
                    isIncluded: true,
                    isHidden: _item.isHidden
                })
            } else {
                _items.push({
                    level: _item.level,
                    simplify: 1,
                    isIncluded: false,
                    isHidden: _item.isHidden
                })
            }
        }
        this._divRoot.render(<ZoomInfo map={this._map} data={_items} toggleVisibilityLayer={this._toggleVisibilityLayer} onApplyAtZoomLevel={this._onApplyAtZoomLevel} />);
    }
}

interface AdminLevelSimplifyFactor {
    zoom_level: number;
    simplify: number;
}

interface GeoJSONFileMeta {
    level: number;
    factors: AdminLevelSimplifyFactor[];
    has_data: boolean;
    isHidden?: boolean;
}

interface GeoJSONFile {
    [level: number]: React.MutableRefObject<any>;
}

interface CountryItem {
    id: number;
    label: string;
}

export default function TilingConfigPreview(props: any) {
    const mapContainer = useRef(null);
    const map = useRef(null);
    const mapControlRef = useRef(null);
    const [lng] = useState(139.753);
    const [lat] = useState(35.6844);
    const [zoom, setZoom] = useState(0);
    const [bbox, setBbox] = useState<any>(null)
    const [loading, setLoading] = useState(false)
    const [mapLoaded, setMapLoaded] = useState(false)
    const [minZoom, setMinZoom] = useState(0);
    const [maxZoom, setMaxZoom] = useState(8);
    const [files, setFiles] = useState<GeoJSONFileMeta[]>([])
    const [countries, setCountries] = useState<CountryItem[]>([])
    const [selectedAdm0Id, setSelectedAdm0Id] = useState<number>(0)
    const prevSelectedAdm0Id = usePrevious(selectedAdm0Id)
    const [datasetRefs, setDatasetRefs] = useState<GeoJSONFile>({})

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

    const fetchTempTilingConfig = () => {
        let _fetch_url = `${TILING_CONFIGS_TEMP_DETAIL_URL}${props.session}/`
        if (props.viewUUID) {
            _fetch_url = _fetch_url + `?view_uuid=${props.viewUUID}`
        } else if (props.datasetUUID) {
            _fetch_url = _fetch_url + `?dataset_uuid=${props.datasetUUID}`
        }
        if (selectedAdm0Id > 0) {
            _fetch_url = _fetch_url + `&adm0_id=${selectedAdm0Id}`
        }
        if (Object.keys(datasetRefs).length > 0) {
            removeLayers(datasetRefs)
        }
        setDatasetRefs({})
        setLoading(true)
        axios.get(_fetch_url).then(
            response => {
                let _data = response.data
                setMinZoom(_data.min_zoom)
                setMaxZoom(_data.max_zoom)
                let _countries = _data.countries as CountryItem[]
                setCountries(_countries)
                if (_countries.length > 0 && selectedAdm0Id === 0) {
                    setSelectedAdm0Id(_countries[0].id)
                }
                let _levels = _data.levels as GeoJSONFileMeta[]
                setFiles([..._levels])
                setLoading(false)
            }
        ).catch((error) => {
            console.log('error fetchTempTilingConfig ', error)
            setLoading(false)
        })
    }

    useEffect(() => {
        if (!mapLoaded) return
        fetchTempTilingConfig()
    }, [mapLoaded]);

    useEffect(() => {
        mapFitBounds()
    }, [bbox])

    useEffect(() => {
        if (mapLoaded) return;
        if (map.current) return; //stops map from intializing more than once
        let _style_url = MAP_STYLE_ORIGINAL_URL 
        map.current = new maplibregl.Map({
            container: mapContainer.current,
            style: _style_url,
            center: [lng, lat],
            zoom: 0,
            attributionControl: false,
            minZoom: minZoom,
            maxZoom: maxZoom
        });
        map.current.addControl(new AttributionControl(), 'bottom-left');
        map.current.on('load', () => {
            setMapLoaded(true)
            mapFitBounds()
        })
        mapControlRef.current = new MapControl(toggleVisibilityLayer, onApplyAtZoomLevel)
        map.current.addControl(mapControlRef.current, 'top-left')
        map.current.on('zoom', () => {
            let _zoom = Math.trunc(map.current.getZoom())
            if (_zoom !== zoom) {
                setZoom(_zoom)
            }
        })
    }, [])

    useEffect(() => {
        if (files.length === 0) return;
        if (selectedAdm0Id === 0) return;

        if (Object.keys(datasetRefs).length === 0) {
            setLoading(true)
            // do fetch all geojson levels
            let _fetchApis = []
            for (const _file of files) {
                if (_file.has_data) {
                    _fetchApis.push(fetchGeoJson(selectedAdm0Id, _file.level))
                }
            }
            Promise.all(_fetchApis).then((responses) => {
                processGeoJsonData(responses, files)
                setLoading(false)
            }).catch((error) => {
                setLoading(false)
                console.log('Error fetching geojson! ', error)
            })
        } else {
            // hide/show layers
            drawLayers(datasetRefs, files, zoom)
        }
        if (mapControlRef.current) {
            mapControlRef.current.setData(files, toggleVisibilityLayer, onApplyAtZoomLevel)
        }
    }, [files])

    useEffect(() => {
        if (!mapLoaded) return
        if (selectedAdm0Id > 0 && prevSelectedAdm0Id > 0) {
            fetchTempTilingConfig()
        }
    }, [selectedAdm0Id, mapLoaded])

    useEffect(() => {
        if (files.length === 0) return;
        if (selectedAdm0Id === 0) return;
        if (Object.keys(datasetRefs).length === 0) return;
        if (mapControlRef.current) {
            mapControlRef.current.setData(files, toggleVisibilityLayer, onApplyAtZoomLevel)
        }
        drawLayers(datasetRefs, files, zoom)
    }, [zoom])

    const fetchGeoJson = (adm0Id: number, level: number) => {
        let _fetch_url = `${PREVIEW_GEOJSON_URL}?adm0_id=${adm0Id}&level=${level}`
        if (props.viewUUID) {
            _fetch_url = _fetch_url + `&view_uuid=${props.viewUUID}`
        } else if (props.datasetUUID) {
            _fetch_url = _fetch_url + `&dataset_uuid=${props.datasetUUID}`
        }
        return axios.get(_fetch_url)
    }

    const removeLayers = (refs: GeoJSONFile) => {
        if (!map.current) return;
        for (const [key, value] of Object.entries(refs)) {
            const _level = parseInt(key)
            let _sourceName = `map-level-${_level}`
            let _layerName = `${_sourceName}-layer`
            if (map.current.getLayer(_layerName)) {
                map.current.removeLayer(_layerName)
            }
            if (map.current.getSource(_sourceName)) {
                map.current.removeSource(_sourceName)
            }
        }
    }

    const toggleLayer = (level: number, isShow: boolean) => {
        if (!map.current) return;
        let _sourceName = `map-level-${level}`
        let _layerName = `${_sourceName}-layer`
        if (!map.current.getLayer(_layerName)) return;
        map.current.setLayoutProperty(
            _layerName,
            'visibility',
            isShow ? 'visible' : 'none'
        );
    }

    const processGeoJsonData = useCallback((responses: any, fileMetas: GeoJSONFileMeta[]) => {
        let _refs: GeoJSONFile = {}
        let _fileMetaWithData = fileMetas.filter((fileMeta) => fileMeta.has_data)
        for (let i = 0; i < responses.length; ++i) {
            let _file = _fileMetaWithData[i]
            _refs[_file.level] = createRef()
            var data = {
                content: responses[i].data,
                filename: `adm0-${selectedAdm0Id}-level-${_file.level}.geojson`
            }
            _refs[_file.level].current = mapshaper.internal.importContent({
                json: data
            }, {})
        }
        drawLayers(_refs, fileMetas, zoom)
        setDatasetRefs(_refs)
    }, [zoom, selectedAdm0Id])

    const drawLayers = (refs: GeoJSONFile, files: GeoJSONFileMeta[], currentZoom: number) => {
        if (!map.current) return;
        for (const [key, value] of Object.entries(refs)) {
            const _level = parseInt(key)
            let _sourceName = `map-level-${_level}`
            let _layerName = `${_sourceName}-layer`
            let _source = map.current.getSource(_sourceName)
            // find if level has meta
            let _searchIdx = files.findIndex((file) => file.level === _level)
            if (_searchIdx === -1) continue
            let _file = files[_searchIdx]
            let _searchFactorIdx = _file.factors.findIndex((factor) => factor.zoom_level == currentZoom)
            if (_searchFactorIdx === -1) {
                // remove from map
                toggleLayer(_level, false)
            } else {
                // do simplification if needed
                let _factor = _file.factors[_searchFactorIdx]
                let _currentSimplify = value.current.info.simplify?.percentage
                let _simplified = false
                if ((_currentSimplify === undefined && _factor.simplify < 1) ||
                    (_currentSimplify !== undefined && _currentSimplify !== _factor.simplify)) {
                    console.log('do simplify with ', _sourceName, _factor.simplify)
                    let simplifyOpts = {
                        method: 'dp',
                        percentage: _factor.simplify, // 1 %
                        no_repair: true,
                        keep_shapes: true,
                        planar: false
                    }
                    mapshaper.cmd.simplify(value.current, simplifyOpts)
                    _simplified = true
                }
                if (_source) {
                    if (_simplified) {
                        let output = mapshaper.internal.exportFileContent(value.current, {
                            format: 'geojson',
                            gj2008: true
                        })
                        map.current.getSource(_sourceName).setData(JSON.parse(output[0].content))
                    }
                    toggleLayer(_level, !_file.isHidden)
                } else {
                    let output = mapshaper.internal.exportFileContent(value.current, {
                        format: 'geojson',
                        gj2008: true
                    })
                    map.current.addSource(_sourceName, {
                        'type': 'geojson',
                        'data': JSON.parse(output[0].content)
                    });
                    map.current.addLayer({
                        'id': _layerName,
                        'type': 'line',
                        'source': _sourceName,
                        'layout': {'visibility': _file.isHidden ? 'none':'visible'},
                        "paint": {
                            "line-color": VECTOR_LINE_COLORS[_level],
                            "line-width": 1
                        }
                    });
                }
            }
        }
    }

    const toggleVisibilityLayer = useCallback((adminLevel: number) => {
        let _files = files.map((file) => {
            if (file.level === adminLevel) {
                file.isHidden = !file.isHidden
            }
            return file
        })
        setFiles(_files)
    }, [files])

    const onApplyAtZoomLevel = useCallback((zoomLevel: number, items: AdminLevelSimplification[]) => {
        let _zoom = Math.trunc(zoomLevel)
        let _files = files.map((file) => {
            let _zoomIdx = file.factors.findIndex((factor) => factor.zoom_level === _zoom)
            let _levelIdx = items.findIndex((item) => item.level === file.level)
            if (_levelIdx > -1) {
                let _item = items[_levelIdx]
                let _factors = [...file.factors]
                if (_zoomIdx === -1) {
                    if (_item.isIncluded) {
                        _factors.push({
                            simplify: _item.simplify,
                            zoom_level: _zoom
                        })
                    }
                } else {
                    if (_item.isIncluded) {
                        _factors[_zoomIdx] = {
                            simplify: _item.simplify,
                            zoom_level: _zoom
                        }
                    } else {
                        // remove if not included in zoom level
                        _factors.splice(_zoomIdx, 1)
                    }
                }
                file.factors = _factors
            }
            return {...file}
        })
        // save configs
        let _save_url = `${TILING_CONFIGS_TEMP_SAVE_URL}${props.session}/`
        let data: TilingConfig[] = []
        for (let _file of files) {
            for (let _factor of _file.factors) {
                let _zoomIdx = data.findIndex((d) => d.zoom_level === _factor.zoom_level)
                if (_zoomIdx === -1) {
                    data.push({
                        zoom_level: _factor.zoom_level,
                        admin_level_tiling_configs: [{
                            level: _file.level,
                            simplify_tolerance: _factor.simplify
                        }]
                    })
                } else {
                    data[_zoomIdx].admin_level_tiling_configs.push({
                        level: _file.level,
                        simplify_tolerance: _factor.simplify
                    })
                }
            }
        }
        setLoading(true)
        postData(_save_url, data).then(
            response => {
                setLoading(false)
                setFiles(_files)
            }
          ).catch(error => {
            setLoading(false)
            console.log('error ', error)
        })
    }, [files])

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
                <div className='map-wrap'>
                    <div ref={mapContainer} className='map' />
                </div>
            </div>
            <div className="button-container" style={{marginLeft:0, width: '100%', padding: '10px'}}>
                <Grid container direction='row' justifyContent='space-between' sx={{paddingRight: '20px'}}>
                    <Grid item>
                        <Button disabled={loading} onClick={() => props.onBackClicked()} variant="outlined">
                            Back
                        </Button>
                    </Grid>
                    <Grid item sx={{ display: 'flex' }}>
                        {!loading && mapLoaded && 
                            <FormControl sx={{minWidth: '180px'}}>
                                <InputLabel id="country-select-label">Select Country</InputLabel>
                                <Select
                                    labelId="country-select-label"
                                    id="country-select"
                                    value={selectedAdm0Id.toString()}
                                    onChange={(event: SelectChangeEvent) => {
                                        setSelectedAdm0Id(parseInt(event.target.value))
                                    }}
                                >
                                    { countries.map((value, index) => {
                                        return <MenuItem key={index} value={value.id}>{value.label}</MenuItem>
                                    })}
                                </Select>
                            </FormControl>
                        }
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
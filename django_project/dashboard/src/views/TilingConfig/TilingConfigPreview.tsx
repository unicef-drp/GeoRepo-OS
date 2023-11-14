import React, {useEffect, useState, useRef, createRef, useCallback} from 'react';
import axios from "axios";
import Grid from '@mui/material/Grid';
import FormControl from '@mui/material/FormControl';
import maplibregl, {AttributionControl, Map} from "maplibre-gl";
import { usePrevious } from '../../utils/Helpers';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import Dataset from '../../models/dataset';
import View from '../../models/view';
import { TilingConfig, ZOOM_LEVELS, MAX_ZOOM } from '../../models/tiling';
import HtmlTooltip from '../../components/HtmlTooltip';

const TILING_CONFIGS_TEMP_DETAIL_URL = '/api/tiling-configs/preview/country/list/'
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
    bbox?: string;
}

interface TilingConfigPreviewInterface {
    configData: TilingConfig[];
    dataset?: Dataset;
    view?: View;
    onGeoJsonLoading?: (isLoading: boolean) => void;
    disabled?: boolean;
}


export default function TilingConfigPreview(props: TilingConfigPreviewInterface) {
    const mapContainer = useRef(null);
    const map = useRef(null);
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
    const [availableLevels, setAvailableLevels] = useState<number[]>([])

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

    const fetchTilingConfigCountryList = () => {
        // levels update -> files update -> fetch geojson for each level
        if (props.onGeoJsonLoading) {
            props.onGeoJsonLoading(true)
        }
        let _fetch_url = `${TILING_CONFIGS_TEMP_DETAIL_URL}`
        if (props.view && props.view.uuid) {
            _fetch_url = _fetch_url + `?view_uuid=${props.view.uuid}`
        } else if (props.dataset && props.dataset.uuid) {
            _fetch_url = _fetch_url + `?dataset_uuid=${props.dataset.uuid}`
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
                let _countries = _data.countries as CountryItem[]
                setCountries(_countries)
                if (_countries.length > 0 && selectedAdm0Id === 0) {
                    setSelectedAdm0Id(_countries[0].id)
                }
                setAvailableLevels(_data.levels as number[])
                if (_data.levels && _data.levels.length === 0) {
                    if (props.onGeoJsonLoading) {
                        props.onGeoJsonLoading(false)
                    }
                }
                setLoading(false)
            }
        ).catch((error) => {
            console.log('error fetchTempTilingConfig ', error)
            setLoading(false)
            if (props.onGeoJsonLoading) {
                props.onGeoJsonLoading(false)
            }
        })
    }

    useEffect(() => {
        if (!props.configData) return
        if (availableLevels.length === 0) return
        let _sorted = props.configData.sort((a, b) => a.zoom_level - b.zoom_level)
        setMinZoom(_sorted[0].zoom_level)
        setMaxZoom(_sorted[_sorted.length - 1].zoom_level)
        let _fileMetas: { [id: number] : GeoJSONFileMeta; } = {}
        for (let i=0;i<_sorted.length;++i) {
            let _configs = _sorted[i].admin_level_tiling_configs
            for (let j=0;j<_configs.length;++j) {
                let _config = _configs[j]
                if (!(_config.level in _fileMetas)) {
                    _fileMetas[_config.level] = {
                        level: _config.level,
                        factors: [],
                        has_data: availableLevels.includes(_config.level)
                    }
                }
                _fileMetas[_config.level]['factors'].push({
                    zoom_level: _sorted[i].zoom_level,
                    simplify: _config.simplify_tolerance
                })
            }
        }
        setFiles(Object.keys(_fileMetas).map(function(key:any){
            return _fileMetas[key]
        }))
    }, [props.configData, availableLevels])

    useEffect(() => {
        if (!mapLoaded) return
        fetchTilingConfigCountryList()
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
            minZoom: 0,
            maxZoom: MAX_ZOOM
        });
        map.current.addControl(new AttributionControl(), 'bottom-left');
        map.current.on('load', () => {
            setMapLoaded(true)
            mapFitBounds()
        })
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
                if (props.onGeoJsonLoading) {
                    props.onGeoJsonLoading(false)
                }
                setLoading(false)
            }).catch((error) => {
                setLoading(false)
                if (props.onGeoJsonLoading) {
                    props.onGeoJsonLoading(false)
                }
                console.log('Error fetching geojson! ', error)
            })
        } else {
            // hide/show layers
            drawLayers(datasetRefs, files, zoom)
        }
    }, [files])

    useEffect(() => {
        if (!mapLoaded) return
        if (selectedAdm0Id > 0 && prevSelectedAdm0Id > 0) {
            fetchTilingConfigCountryList()
        }
    }, [selectedAdm0Id, mapLoaded])

    useEffect(() => {
        if (files.length === 0) return;
        if (selectedAdm0Id === 0) return;
        if (Object.keys(datasetRefs).length === 0) return;
        drawLayers(datasetRefs, files, zoom)
    }, [zoom])

    const fetchGeoJson = (adm0Id: number, level: number) => {
        let _fetch_url = `${PREVIEW_GEOJSON_URL}?adm0_id=${adm0Id}&level=${level}`
        if (props.view && props.view.uuid) {
            _fetch_url = _fetch_url + `&view_uuid=${props.view.uuid}`
        } else if (props.dataset && props.dataset.uuid) {
            _fetch_url = _fetch_url + `&dataset_uuid=${props.dataset.uuid}`
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
                // remove from map only if the current zoom is lower than max zoom
                if (currentZoom <= maxZoom) {
                    toggleLayer(_level, false)
                }
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

    const zoomToAdm0Bbox = (adm0Id: number) => {
        let _idx = countries.findIndex((country) => country.id === adm0Id)
        if (_idx === -1) return
        let _country = countries[_idx]
        if (_country.bbox) {
            let _bbox = JSON.parse(_country.bbox)
            setBbox(_bbox)
        }
    }

    useEffect(() => {
        if (selectedAdm0Id) {
            zoomToAdm0Bbox(selectedAdm0Id)
        }
    }, [selectedAdm0Id])

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
                <div className='map-wrap'>
                    <div ref={mapContainer} className='map' />
                </div>
            </div>
            <div className="button-container" style={{marginLeft:0, width: '100%', paddingTop: '10px'}}>
                <Grid container direction='row' justifyContent='space-between'>
                    <Grid item>
                        <Grid container flexDirection={'row'} alignItems={'center'}>
                            <Grid item>
                                <h4>Live Preview</h4>
                            </Grid>
                            <Grid item>
                                <HtmlTooltip tooltipTitle='Live Preview'
                                    tooltipDescription={
                                        <p>
                                            This is a live preview. The tiles you see in the map are being dynamically generated. 
                                            After you click save, the view will be marked as inconsistent - you should visit the sync status tab to trigger the generation of cached tiles.
                                        </p>
                                    }
                                />
                            </Grid>
                        </Grid>
                    </Grid>
                    <Grid item>
                        {mapLoaded && 
                            <FormControl sx={{minWidth: '180px'}} disabled={loading || props.disabled}>
                                <InputLabel id="zoom-select-label">Zoom Level</InputLabel>
                                <Select
                                    labelId="zoom-select-label"
                                    id="zoom-select"
                                    label="Zoom Level"
                                    value={zoom.toString()}
                                    onChange={(event: SelectChangeEvent) => {
                                        if (map.current) {
                                            map.current.flyTo({
                                                center: map.current.getCenter(),
                                                zoom: parseInt(event.target.value),
                                                speed: 0.8,
                                                essential: true
                                            })
                                        }
                                    }}
                                >
                                    { ZOOM_LEVELS.map((value, index) => {
                                        return <MenuItem key={index} value={value}>{value}</MenuItem>
                                    })}
                                </Select>
                            </FormControl>
                        }
                    </Grid>
                    <Grid item>
                        {mapLoaded && 
                            <FormControl sx={{minWidth: '180px'}} disabled={loading || props.disabled}>
                                <InputLabel id="country-select-label">Country</InputLabel>
                                <Select
                                    labelId="country-select-label"
                                    id="country-select"
                                    label="Country"
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
                </Grid>
            </div>
        </div>
    )
}
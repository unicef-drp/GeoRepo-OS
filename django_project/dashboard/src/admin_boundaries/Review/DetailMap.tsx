import React, {useEffect, useRef, useState} from "react";
import maplibregl, {AttributionControl, ControlPosition, IControl, Map} from "maplibre-gl";
import {Skeleton} from "@mui/material";
import {UploadSession, BoundaryData} from '../../models/upload';
import '../../styles/Review.scss';

const MAP_STYLE_URL = window.location.origin + '/api/dataset-style/review/'

interface ReviewMapInterface {
    bbox: any;
    mainBoundary: any;
    comparisonBoundary: any;
    uploadSession: UploadSession;
    selectedLevel: string;
    mainBoundaryData?: BoundaryData;
    comparisonBoundaryData?: BoundaryData;
}

class MatchBoundaryControl implements IControl {
    _map: Map;
    _container: HTMLElement;
    _innerContainer: HTMLElement;
    _mainBoundaryTextItem: HTMLElement;
    _comparisonBoundaryTextItem: HTMLElement;

    onAdd(map: Map): HTMLElement {
        this._map = map;
        this._container = this._create('div', 'maplibregl-ctrl maplibregl-ctrl-attrib mapboxgl-ctrl mapboxgl-ctrl-attrib legends');
        this._innerContainer = this._create('div', 'maplibregl-ctrl-attrib-inner mapboxgl-ctrl-attrib-inner', this._container);
        let legendsContainer = this._create('div', 'legends-content', this._innerContainer);
        let mainBoundaryItem = this._create('div', 'legends-item', legendsContainer);
        let mainLegendLine = this._create('div', 'main-boundary-lines');
        mainLegendLine.innerHTML = '<hr />';
        mainBoundaryItem.appendChild(mainLegendLine);
        this._mainBoundaryTextItem = this._create('span', '', mainBoundaryItem);
        this._mainBoundaryTextItem.innerHTML = 'New Entity';

        let comparisonBoundaryItem = this._create('div', 'legends-item', legendsContainer);
        let comparisonLegendLine = this._create('div', 'comparison-boundary-lines');
        comparisonLegendLine.innerHTML = '<hr />';
        comparisonBoundaryItem.appendChild(comparisonLegendLine);
        this._comparisonBoundaryTextItem = this._create('span', '', comparisonBoundaryItem);
        this._comparisonBoundaryTextItem.innerHTML = 'Matching Entity';

        this._container.style.display = 'none';
        return this._container;
    }

    onRemove(map: Map): void {
        this._remove(this._container);

        this._map = undefined;
    }

    _create<K extends keyof HTMLElementTagNameMap>(tagName: K, className?: string, container?: HTMLElement): HTMLElementTagNameMap[K] {
        const el = window.document.createElement(tagName);
        if (className !== undefined) el.className = className;
        if (container) container.appendChild(el);
        return el;
    }

    _remove(node: HTMLElement) {
        if (node.parentNode) {
            node.parentNode.removeChild(node);
        }
    }

    hide(): void {
        this._container.style.display = 'none';
    }

    setMainBoundaryText(entityName: string, entityCode: string): void {
        if (entityName  && entityCode) {
            this._mainBoundaryTextItem.innerHTML = `${entityName} - ${entityCode}`
        } else {
            this._mainBoundaryTextItem.innerHTML = `New Entity`
        }
        
        this._container.style.display = 'block';
    }

    setComparisonBoundaryText(entityName: string, entityCode: string): void {
        if (entityName  && entityCode) {
            this._comparisonBoundaryTextItem.innerHTML = `${entityName} - ${entityCode}`
        } else {
            this._comparisonBoundaryTextItem.innerHTML = `Matching Entity`
        }
        this._container.style.display = 'block';
    }
}


export default function ReviewMap(props: ReviewMapInterface) {

    const mapContainer = useRef(null);
    const map = useRef(null);
    const legendControl = useRef(null);
    const [lng] = useState(139.753);
    const [lat] = useState(35.6844);
    const [zoom] = useState(1);
    const [loading, setLoading] = useState(true)
    const [mapLoaded, setMapLoaded] = useState(false)
    const [mainBoundaryAdded, setMainBoundaryAdded] = useState<boolean>(false)
    const [comparisonBoundaryAdded, setComparisonBoundaryAdded] = useState<boolean>(false)

    const mapFitBounds = () => {
        if (props.bbox && map.current) {
            map.current.fitBounds(
              props.bbox,
              {
                  padding: {top: 10, bottom:25, left: 20, right: 20}
              }
            )
        }
    }

    useEffect(() => {
        mapFitBounds()
    }, [props.bbox])

    useEffect(() => {
        if (!mapLoaded) return;
        // Draw main boundary
        if (props.mainBoundary) {
            if (map.current) {
                if (!props.comparisonBoundary && comparisonBoundaryAdded) {
                    map.current.removeLayer('comparisonBoundary');
                    map.current.removeSource('comparisonBoundary');
                    setComparisonBoundaryAdded(false)
                }
                if (mainBoundaryAdded) {
                    map.current.removeLayer('mainBoundary');
                    map.current.removeSource('mainBoundary');
                } else {
                    // remove source
                    map.current.getStyle().layers.forEach((layer:any) => {
                        if(layer.id.match(/level_(\d+)/g) && layer.source==props.uploadSession.datasetStyleSource){
                           map.current.removeLayer(layer.id)
                          }
                      })
                    map.current.removeSource(props.uploadSession.datasetStyleSource)
                }
                 map.current.addSource('mainBoundary', {
                    'type': 'geojson',
                    'data': props.mainBoundary
                })
                setMainBoundaryAdded(true)
                map.current.addLayer({
                    'id': 'mainBoundary',
                    'type': 'line',
                    'source': 'mainBoundary',
                    'layout': {},
                    'paint': {
                        'line-color': '#32cd32',
                        'line-width': 6
                    }
                });
            }
        }
    }, [props.mainBoundary, mapLoaded])

     useEffect(() => {
        if (!mapLoaded) return;
        // Draw comparison boundary
        if (props.comparisonBoundary) {
            if (map.current) {
                 if (comparisonBoundaryAdded) {
                    map.current.removeLayer('comparisonBoundary');
                    map.current.removeSource('comparisonBoundary');
                 }
                map.current.addSource('comparisonBoundary', {
                    'type': 'geojson',
                    'data': props.comparisonBoundary
                })
                setComparisonBoundaryAdded(true)
                map.current.addLayer({
                    'id': 'comparisonBoundary',
                    'type': 'line',
                    'source': 'comparisonBoundary',
                    'layout': {},
                    'paint': {
                        'line-dasharray': [2,2],
                        'line-color': '#FF2400',
                        'line-width': 2
                    }
                });
            }
        }
    }, [props.comparisonBoundary, mapLoaded])

    useEffect(() => {
        if (!legendControl.current) return;
        if (props.mainBoundaryData === null && props.comparisonBoundaryData === null) {
            legendControl.current.hide()
            return
        }
        if (props.mainBoundaryData) {
            legendControl.current.setMainBoundaryText(props.mainBoundaryData.label, props.mainBoundaryData.code)
        } else {
            legendControl.current.setMainBoundaryText(null, null)
        }
        if (props.comparisonBoundaryData) {
            legendControl.current.setComparisonBoundaryText(props.comparisonBoundaryData.label, props.comparisonBoundaryData.code)
        } else {
            legendControl.current.setComparisonBoundaryText(null, null)
        }
    }, [props.mainBoundaryData, props.comparisonBoundaryData, mapLoaded])

    useEffect(() => {
        if (!loading) {
            if (map.current) return; //stops map from intializing more than once
            if (props.uploadSession.datasetUuid && props.uploadSession.revisedEntityUuid && props.selectedLevel !== null) {
                let _style_url = `${MAP_STYLE_URL}${props.uploadSession.datasetUuid}/${props.selectedLevel}/${props.uploadSession.revisedEntityUuid}/`
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
                legendControl.current = new MatchBoundaryControl()
                map.current.addControl(legendControl.current, 'bottom-left')
            }
        }
    }, [loading])

    useEffect(() => {
        if (map.current && props.uploadSession.datasetUuid && props.uploadSession.revisedEntityUuid && props.selectedLevel !== null) {
            let _style_url = `${MAP_STYLE_URL}${props.uploadSession.datasetUuid}/${props.selectedLevel}/${props.uploadSession.revisedEntityUuid}/`
            map.current.setStyle(_style_url)
            // reset variables
            setMainBoundaryAdded(false)
            setComparisonBoundaryAdded(false)
        }
    }, [props.selectedLevel])

    useEffect(() => {
        setTimeout(() => {
            setLoading(false)
        }, 200)
    }, []);

    let _preferences: any = window.preferences
    let _maptiler = _preferences ? _preferences['maptiler_api_key'] : ''
    return (
    <div className="map-wrap review-map">
        {_maptiler ? null : <h2>Please set Maptiler API Key on the admin!</h2>}
        { loading ?
            <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> :
            <div ref={mapContainer} className="map" />}
      </div>
    )
}

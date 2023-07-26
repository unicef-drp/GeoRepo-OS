import React, {useEffect, useRef, useState} from "react";
import maplibregl, {AttributionControl} from "maplibre-gl";
import {Skeleton} from "@mui/material";
import { UploadSession } from "../../models/upload";

const MAP_STYLE_URL = window.location.origin + '/api/dataset-style/review/'

interface ReviewMapInterface {
    bbox: any,
    mainBoundary: any,
    uploadSession: UploadSession,
    selectedType: string
}

export default function ReviewMap(props: ReviewMapInterface) {

    const mapContainer = useRef(null);
    const map = useRef(null);
    const [lng] = useState(139.753);
    const [lat] = useState(35.6844);
    const [zoom] = useState(1);
    const [loading, setLoading] = useState(true)
    const [mapLoaded, setMapLoaded] = useState(false)
    const [mainBoundaryAdded, setMainBoundaryAdded] = useState<boolean>(false)

    const mapFitBounds = () => {
        if (props.bbox && props.bbox.length && map.current) {
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
    }, [props.mainBoundary])

    useEffect(() => {
        if (!loading) {
            if (map.current) return; //stops map from intializing more than once
            if (props.uploadSession.datasetUuid && props.selectedType) {
                let _style_url = `${MAP_STYLE_URL}${props.uploadSession.datasetUuid}/revision/${props.uploadSession.revisionNumber}/boundary_type/${props.selectedType}/`
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
        }
    }, [loading])

    useEffect(() => {
        setTimeout(() => {
            setLoading(false)
        }, 200)
    }, []);

    return (
    <div className="map-wrap">
        { loading ?
            <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> :
            <div ref={mapContainer} className="map" />}
      </div>
    )
}

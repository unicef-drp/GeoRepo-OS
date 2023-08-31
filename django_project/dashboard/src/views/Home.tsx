import React, {useEffect, useRef, useState} from "react";
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import '../styles/Home.scss';


export default function Home() {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [lng] = useState(139.753);
  const [lat] = useState(35.6844);
  const [zoom] = useState(1);
  let _preferences: any = window.preferences
  let _maptiler = _preferences ? _preferences['maptiler_api_key'] : ''

  useEffect(() => {
    if (map.current) return; //stops map from intializing more than once
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: `https://api.maptiler.com/maps/streets/style.json?key=${_maptiler}`,
      center: [lng, lat],
      zoom: zoom
    });
  });
  return (
    <div className="AdminContentMain">
      <h1>GeoRepo</h1>
      {_maptiler ? null : <h2>Please set Maptiler API Key on the admin!</h2>}
      <div className="map-wrap">
        <div ref={mapContainer} className="map" />
      </div>
    </div>
  )
}

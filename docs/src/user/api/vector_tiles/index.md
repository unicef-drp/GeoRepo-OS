---
title: GeoRepo-OS Documentation API Guide
summary: GeoRepo is a UNICEF’s geospatial web-based data storage and administrative boundary harmonization platform.
    - Tim Sutton
    - Dimas Tri Ciputra
    - Danang Tri Massandy
date: 2023-08-03
some_url: https://github.com/unicef-drp/GeoRepo-OS
copyright: Copyright 2023, Unicef
contact: georepo-no-reply@unicef.org
license: This program is free software; you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.
#context_id: 1234
---

# Vector Tiles Guide

The user can access the vector tiles from a view. The user must retrieve
the vector tiles URL from below APIs:

- Get views by dataset: /search/dataset/{uuid}/view/list/
- Get views that user can access: /search/view/list/
- Find view detail: /search/view/{uuid}/

The vector tiles URL is available in the `vector_tiles` field from the API response.
The returned URL will be in the XYZ template with the following format:

```
https://georepo.unicef.org/layer_tiles/809ad72b-f083-4f2f-aca0-e756482dbd6d/{z}/{x}/{y}?t=1700218824
```

where `809ad72b-f083-4f2f-aca0-e756482dbd6d` is the resource ID from the View. The request parameter `t` is the last updated time for the vector tiles.


## How to authenticate to the vector tiles

The vector tiles requires [API KEY](../guide/index.md#generating-an-api-key) and your `email address` for the authentication. This is similar to how to call the GeoRepo API, but the different is the `API KEY` and your `email address` need to be appened to the vector tiles URL as a request parameters. Below format is a complete vector tiles URL with the `API KEY` and `email address`:

```
https://georepo.unicef.org/layer_tiles/809ad72b-f083-4f2f-aca0-e756482dbd6d/{z}/{x}/{y}?t=1700218824&&token=YOUR_API_KEY&georepo_user_key=YOUR_EMAIL_ADDRESS
```

where YOUR_API_KEY is the `API KEY` and YOUR_EMAIL_ADDRESS  is your `email address`.


## Vector Tiles Response Codes

- 200: success response
- 401: missing authentication details
- 403: user does not have access to the resource in the view
- 404: vector tile at coordinate {x}, {y}, and zoom level {z} does not exist


## Best Practices

### Caching on Client Application

The client application should cache the vector tiles by using `Cache-Control` directive in the response header. By default, the cache expires in 21 days.
When there is an update to the vector tiles content, the vector tiles URL will be regenerated with a new `t` value. Most of the map client (e.g. maplibre, mapbox, or leaflet JS) will automatically do the caching of the vector tiles.

### Apply Bounding Box in the Map

The GeoRepo APIs that return the vector tiles URL will also return bounding box (`bbox` field) for the view. The map client should use this bounding box so the map client does not request coordinate that the vector tile does not exist.

### Apply Overzoom in the Map

The GeoRepo APIs also returns the maximum zoom (`max_zoom` field) for the view. The map client can use this value to apply the overzoom so the map does not request vector tiles above the `max_zoom`.

### Sample code

Below is sample code to load the vector tiles using Maplibre.

```
var map = new maplibregl.Map({
    container: 'map',
    zoom: 5,
    center:  [0, 0] 
});
map.on('load', function () {
    map.addSource('World (Latest)', {
        'type': 'vector',
        "tiles": ["https://georepo.unicef.org/layer_tiles/809ad72b-f083-4f2f-aca0-e756482dbd6d/{z}/{x}/{y}?t=1700218824&&token=YOUR_API_KEY&georepo_user_key=YOUR_EMAIL_ADDRESS"],
        "tolerance": 0,
        "minzoom": 0,
        "maxzoom": MAX_ZOOM_VALUE
    });

    map.fitBounds([BOUNDING_BOX_VALUE])
    
    map.addLayer({'id': 'Level-1', 'source': 'World (Latest)', 'source-layer': 'Level-1', 'type': 'line', 'paint': {'line-color': '#76AC1F', 'line-width': 1}, 'minzoom': 2})
    
    map.addLayer({'id': 'Level-0', 'source': 'World (Latest)', 'source-layer': 'Level-0', 'type': 'line', 'paint': {'line-color': '#69C868', 'line-width': 1}, 'minzoom': 0})
});
```

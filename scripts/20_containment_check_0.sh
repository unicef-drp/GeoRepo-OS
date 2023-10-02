#!/usr/bin/env bash
ab -g $1 -n $NUM_OF_REQUESTS -c $NUM_OF_CONCURRENCIES -p containment_check_data.geojson -T application/json -H "Authorization: Token ${TOKEN}" -H "GeoRepo-User-Key: ${EMAIL}" -H "User-Agent: PostmanRuntime/7.32.3" -H "Accept: application/json" $BASE_URL/api/v1/operation/view/$VIEW_UUID/containment-check/ST_Intersects/0/ucode/?admin_level=0

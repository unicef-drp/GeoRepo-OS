#!/usr/bin/env bash
ab -g $1 -n $NUM_OF_REQUESTS -c $NUM_OF_CONCURRENCIES -H "Authorization: Token ${TOKEN}" -H "GeoRepo-User-Key: ${EMAIL}" -H "User-Agent: PostmanRuntime/7.32.3" $BASE_URL/api/v1/search/view/$VIEW_UUID/entity/level/1

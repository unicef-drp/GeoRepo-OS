#!/usr/bin/env bash
ab -g $1 -n $NUM_OF_REQUESTS -c $NUM_OF_CONCURRENCIES -H "Authorization: Token ${TOKEN}" -H "GeoRepo-User-Key: ${EMAIL}" $BASE_URL/api/v1/search/view/$VIEW_UUID/entity/version/concept_ucode/$CONCEPT_UCODE/

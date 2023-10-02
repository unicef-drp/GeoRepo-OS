#!/usr/bin/env bash
ab -g $1 -n 10 -c 2 "${BASE_URL}/layer_tiles/${VT_UUID}/${VT_Z}/${VT_X}/${VT_Y}?t=1696226381&token=${TOKEN}&georepo_user_key=${EMAIL}"
sleep 10

# higher concurrency makes the API slower

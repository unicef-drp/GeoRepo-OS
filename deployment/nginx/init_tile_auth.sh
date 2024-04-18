#!/bin/sh

# create tile_auth dir if not exists
mkdir -p /home/web/nginx_cache/tile_auth

# give permission to nginx user
chown -R nginx:nginx /home/web/nginx_cache/tile_auth

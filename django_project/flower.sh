#!/bin/bash

NAME=flower
DESC="flower daemon"

# Path to virtualenv
ENV_PYTHON="/usr/local/bin/celery"

# Where the Django project is.
FLOWER_CHDIR="/home/web/django_project"

# How to call "manage.py celery flower" (args...)
FLOWERCTL="-A core --broker=redis://default:$REDIS_PASSWORD@$REDIS_HOST flower --port=8080 --url_prefix=/flower --auto_refresh=False --broker_api=redis://default:$REDIS_PASSWORD@$REDIS_HOST"
DAEMON=$FLOWERCTL

set -e

case "$1" in
  start)
        echo -n "Starting $DESC: "
        start-stop-daemon --start --pidfile /var/tmp/$NAME.pid \
            --chdir $FLOWER_CHDIR \
            --background \
            --make-pidfile \
            --exec "$ENV_PYTHON" -- $FLOWERCTL
        echo "$NAME."
        ;;

  stop)
        echo -n "Stopping $DESC: "
        start-stop-daemon --stop --quiet --oknodo \
            --pidfile /var/tmp/$NAME.pid
        rm -f /var/tmp/$NAME.pid
        echo "$NAME."
        ;;
esac

exit 0
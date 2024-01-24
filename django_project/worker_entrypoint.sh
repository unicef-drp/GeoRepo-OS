#!/bin/sh

# Exit script in case of error
set -e

echo $"\n\n\n"
echo "-----------------------------------------------------"
echo "STARTING WORKER COMMAND $(date)"
echo "-----------------------------------------------------"

# remove pids
rm -f /var/run/celery/tile.pid
rm -f /var/run/celery/validate.pid

# copy flower daemon script
rm -f /var/tmp/flower.pid
cp flower.sh /etc/init.d/flower
chmod +x /etc/init.d/flower
update-rc.d flower defaults
sleep 2
/etc/init.d/flower start

TILE_C=${VECTOR_TILE_QUEUE_CONCURRENCY:-1}
VALIDATE_C=${VALIDATE_QUEUE_CONCURRENCY:-3}
EXPORTER_C=${EXPORT_DATA_QUEUE_CONCURRENCY:-1}

# start tile and validate workers
celery -A core multi start tile validate exporter -c:tile $TILE_C -c:validate $VALIDATE_C -c:exporter $EXPORTER_C -Q:tile tegola -Q:validate validation -Q:exporter data_exporter -l INFO --logfile=/proc/1/fd/1

# start default worker
celery -A core worker -l INFO --logfile=/proc/1/fd/1

echo "-----------------------------------------------------"
echo "FINISHED WORKER COMMAND --------------------------"
echo "-----------------------------------------------------"

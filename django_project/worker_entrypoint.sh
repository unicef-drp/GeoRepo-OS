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

# start tile and validate workers
celery -A core multi start tile validate -c:tile 1 -c:validate 3 -Q:tile tegola -Q:validate validation -l INFO

# start default worker
celery -A core worker -l INFO

echo "-----------------------------------------------------"
echo "FINISHED WORKER COMMAND --------------------------"
echo "-----------------------------------------------------"

#!/bin/sh

# Exit script in case of error
set -e

echo $"\n\n\n"
echo "-----------------------------------------------------"
echo "STARTING WORKER COMMAND $(date)"
echo "-----------------------------------------------------"

# cleanup any pymp- directories
rm -rf /tmp/pymp-*

# remove pids
rm -f /var/run/celery/tile.pid
rm -f /var/run/celery/validate.pid
rm -f /var/run/celery/exporter.pid

# copy flower daemon script
rm -f /var/tmp/flower.pid
cp flower.sh /etc/init.d/flower
chmod +x /etc/init.d/flower
update-rc.d flower defaults
sleep 2
/etc/init.d/flower start

# start worker via supervisord
/usr/bin/supervisord -c /supervisord.conf

echo "-----------------------------------------------------"
echo "FINISHED WORKER COMMAND --------------------------"
echo "-----------------------------------------------------"

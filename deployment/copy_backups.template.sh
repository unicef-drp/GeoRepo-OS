#!/usr/bin/env bash

# Get the latest backup from production
SOURCE_FOLDER=/source
SOURCE_SERVER=server

DEST_FOLDER=/destination

echo "copy latest backup file"
scp $SOURCE_SERVER:$SOURCE_FOLDER/backups/$(ssh $SOURCE_SERVER "cd $SOURCE_FOLDER; find $1 -type f -exec stat --format '%Y :%y %n' "{}" \; | sort -nr | cut -d. -f3- | head -1") $DEST_FOLDER/backups

# Restart docker db
DOCKER_DB=georepo_db
echo "restore the backup"
cp revoke.sql $DEST_FOLDER/backups
cp restore.sql $DEST_FOLDER/backups
docker exec $DOCKER_DB su - postgres -c "psql django -f /backups/revoke.sql"
docker exec $DOCKER_DB su - postgres -c "dropdb django"
docker exec $DOCKER_DB su - postgres -c "createdb django"
docker exec $DOCKER_DB su - postgres -c "pg_restore -d django /backups/latest.dmp"
docker exec $DOCKER_DB su - postgres -c "psql django -f /backups/restore.sql"

echo "run migration"
DOCKER_UWSGI=georepo_django
docker exec $DOCKER_UWSGI python manage.py migrate

echo "copy media and tiles"
rsync -avz $SOURCE_SERVER:$SOURCE_FOLDER/media $DEST_FOLDER/media
rsync -avz $SOURCE_SERVER:$SOURCE_FOLDER/tegola_config $DEST_FOLDER/tegola_config
rsync -avz $SOURCE_SERVER:$SOURCE_FOLDER/layer_tiles $DEST_FOLDER/layer_tiles

echo "run collectstatic"
docker exec $DOCKER_UWSGI python manage.py collectstatic --noinput
docker exec $DOCKER_UWSGI uwsgi --reload /tmp/django.pid

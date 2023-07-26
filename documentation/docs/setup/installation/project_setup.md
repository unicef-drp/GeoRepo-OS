# Project Setup

## Clone GeoRepo repository

This will clone GeoRepo repository to your machine

```bash
git clone git@github.com:unicef-drp/GeoRepo.git
```

Add your fork repository as second remote URLs

```bash
git remote add userA git@github.com:userA/GeoRepo.git
```

## Building Containers

Create docker-compose.override.yml and .env file from the template

```bash
cd deployment
cp docker-compose.override.template.yml docker-compose.override.yml
cp .template.env .env
cd ..
```

Change DJANGO_SETTINGS_MODULE in the .env file to point to dev environment:

```text
DJANGO_SETTINGS_MODULE = core.settings.dev
```

Run make build command

```bash
make build
```

## Running Containers

To start the containers, we can use make dev command

```bash
make dev
```

We can verify the containers are running successfully using docker ps command

```bash
docker ps
```

## Run migration command

```bash
make migrate
```

## (Optional) Restoring Database

Copy dump file to georepo_db container

```bash
docker cp db.dump georepo_db:/home/db.dump
docker exec -it georepo_db /bin/bash
```

Before restoring the database, we need to drop existing database using below command:

```bash
psql -h 127.0.0.1 -U docker -c “drop database django with (force);”
```

Run pg_restore

```bash
psql -h 127.0.0.1 -U docker -c “create database django;”
cd /home
pg_restore -h 127.0.0.1 -U docker -d django db.dump
```

### Set GeographicalEntity records with is_latest=True and is_approved=True

Some APIs will fetch entities with is_latest=True and is_approved=True

We can update the entities that we restored from previous step

```bash
psql -h 127.0.0.1 -U docker -d django -c update georepo_geographicalentity  set is_latest = true, is_approved = true;”
```

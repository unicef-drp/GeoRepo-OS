---
title: GeoRepo-OS Documentation Home 
summary: GeoRepo is a UNICEF’s geospatial web-based data storage and administrative boundary harmonization platform.
    - Tim Sutton
    - Dimas Tri Ciputra
    - Danang Tri Massandy
date: 2023-08-03
some_url: https://github.com/unicef-drp/GeoRepo-OS
copyright: Copyright 2023, Unicef
contact: georepo-no-reply@unicef.org
license: This program is free software; you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.
#context_id: 1234
---

# GeoRepo

## QUICK INSTALLATION GUIDE

### Development

This will clone GeoRepo repository to your machine

```bash
git clone git@github.com:unicef-drp/GeoRepo-OS.git
```

Add your fork repository as second remote URLs

```bash
git remote add userA git@github.com:userA/GeoRepo-OS.git
```

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

To start the containers, we can use make dev command

```bash
make dev
```

We can verify the containers are running successfully using docker ps command

```bash
docker ps
```

```bash
make migrate
```



# GeoRepo

GeoRepo is UNICEF’s geospatial web-based data storage and administrative boundary harmonization platform. This data is uploaded to GeoRepo and managed as Reference Datasets. In turn, these datasets are utilized and displayed on the GeoSight data analysis/visualization platform.


## Key Concepts

**Datasets**, also known as Reference Datasets, are groupings containing administrative boundaries for specific countries or regions. Users can upload and organize versions of boundaries as they change over time. Subnational boundaries can be labeled according to the national boundary scheme.

**Views** are virtual datasets that can be isolated from larger areas to display specific data. Users can create country-specific views from global or regional datasets.  Views can include all available versions of a reference dataset, or isolate specific versions of administrative boundaries.

The GeoRepo platform relies on the accuracy and analysis of uploaded files to ensure that datasets are both harmonized and verified. When uploading data, GeoRepo will provide users with an error report highlighting inconsistencies such as overlaps between boundaries and the same boundary over successive versions.

## :ballot_box_with_check: Project activity


[![Build and Test](https://github.com/unicef-drp/GeoRepo-OS/actions/workflows/build-and-test.yaml/badge.svg?branch=develop)](https://github.com/unicef-drp/GeoRepo-OS/actions/workflows/build-and-test.yaml)
[![codecov](https://codecov.io/gh/unicef-drp/gis-geo-repository/branch/develop/graph/badge.svg)](https://codecov.io/gh/unicef-drp/gis-geo-repository/)
[![Build and Test React Application](https://github.com/unicef-drp/GeoRepo-OS/actions/workflows/frontend-test.yaml/badge.svg?branch=develop)](https://github.com/unicef-drp/GeoRepo-OS/actions/workflows/frontend-test.yaml)

## :arrow_down: Quick Installation Guide

For deployment, we use docker so you need to have docker running on the host.

```
git clone git@github.com:unicef-drp/GeoRepo-OS.git
cd GeoRepo-OS/deployment
cp .env.example .env
cp docker-compose.override.template.yml docker-compose.override.yml
cd ../
make build
make devweb
# Wait a few seconds for the DB to start before doing the next command
make migrate
make collectstatic
```

To run the frontend
```
cd dashboard
npm run dev-watch
```

The website will be available at `http://localhost:61102`



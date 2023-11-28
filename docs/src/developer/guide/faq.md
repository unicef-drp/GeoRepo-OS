---
title: GeoRepo-OS Developer FAQ
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

# Frequently Asked Questions for Developers

## Host resolution issues on WSL

Network (DNS) issue on the WSL2/Ubuntu, resulting in error when trying to clone the repo: ``unable to access 'https://github.com/unicef-drp/GeoSight-OS.git/: Could not resolve host: github.com``. The solution was to go through steps described here: https://gist.github.com/coltenkrauter/608cfe02319ce60facd76373249b8ca6 and setting up primary DNS to 8.8.8.8 and secondary to 8.8.4.4


## Unable to connect to docker daemon

When trying to Rebuild and Open we got ``Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?``. 

This issue is likely related to the new Docker Desktop Resource Saver mode. After disabling this option you should be able to rebuild.

---
title: GeoRepo-OS Design Guidelines
summary: GeoRepo is a UNICEF's geospatial web-based data storage and administrative boundary harmonization platform.
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

🚧 This document is still under construction

# Developer Workflows

## Adding a Feature

- Create an Issue
- Wait for it to be added to a Sprint
- Functional Tests
- Playwright Tests
- Write end user documentation

## Fixing a Bug

- Claim an Issue
- Wait for it to be added to a Sprint
- Regression Test
- Implement Fix

## Make PR for Feature/Bug Fix

### Committing To Project

Follow our [commit message conventions](./templates/commit-message-convention.md).

### Pull Request Template

If it has related issues, add links to the issues(like `#123`) in the description.
Fill in the [Pull Request Template](./templates/pull-request-template.md) by check your case.

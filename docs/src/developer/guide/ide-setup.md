---
title: GeoRepo-OS IDE Setup
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

# Setting up your IDE

This section outlines the process for configuring your IDE for development.

🚩 Make sure you have gone through the [Cloning Section](cloning.md) before following these notes.
## VS Code Setup
 
Open the project in VSCode (1️⃣, 2️⃣) by navigating the the place on your file system where you checked out the code in the pre-requisites step above (3️⃣).

![image.png](./img/ide-setup-1.png)

Accept the 'trust authors' prompt

![image.png](./img/ide-setup-2.png)
### Copying the .env

Copy the `template.env` to `.env`
![image.png](./img/ide-setup-3.png)
Edit the `.env` file and change the 

```
DJANGO_SETTINGS_MODULE=core.settings.prod
```
to   

```
DJANGO_SETTINGS_MODULE=core.settings.dev
```

![image.png](./img/ide-setup-4.png)



🪧 Now that you have your IDE set up, we can move on to [building the project](building.md).

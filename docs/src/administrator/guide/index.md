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
# Administrator Guide
<!-- Narrative Instructions on how admin users will use the product/platform -->
<!-- Replace all of the titles with relevant titles -->

## Configure Site Name Settings

Go to the Django Admin Page and click on `Sites` tab.

![](./img/admin-sites-tab.png)

Click on row `example.org` to go to the edit page. 

![](./img/admin-sites-edit.png)

Change the `Domain name` and the `Display name` and then click on the `save` button to save the changes.

![](./img/admin-sites-form.png)


## Configure Unicef Group as Default Group for new Unicef User

Go to the Django Admin Page and click on `Registered Domain` tab.

![](./img/admin-registered-domain-tab.png)

Select the `Unicef Group` for domain `unicef.org` and then click on the `Save` button.

![](./img/admin-registered-domain-edit.png)

## Configure Site Preferences

Go to the Django Admin Page and click on `Site preferences` tab.

![](./img/admin-site-preferences-tab.png)

Set the value of `Maptiler api key` that will be used for Map Preview in the dashboard application.

Set the value of `Default admin emails` that will be used for email notification when there is a new sign-up user request and permission access request. Example format: `["admin1@example.org", "admin2@example.org"]`.

![](./img/admin-site-preferences-edit.png)

## Configure Languages

Go to the Django Admin Page and click on `Languages` tab.

![](./img/admin-languages-tab.png)

Click on the `Fetch Languages` button to fetch languages (iso639_1) from this [link](https://restcountries.com/v2/all?fields=name,languages).

![](./img/admin-languages-fetch.png)

## Add Maintenance Message to the dashboard application

Go to the Django Admin Page and click on `Maintenances` tab.

![](./img/admin-maintenances-tab.png)

Click on the `Add maintenance` button.

![](./img/admin-maintenance-add.png)

Fill in the `message`, `scheduled from date`, and `scheduled end date` (optional) and then click the `Save` button.

![](./img/admin-maintenance-form.png)

The maintenance message will be displayed in every page in the dashboard application as shown below.

![](./img/admin-maintenance-preview.png)

To remove the maintenance message, select the item and then select `Delete selected maintenances` from the action dropdown and then click on the `Go` button.

![](./img/admin-maintenance-delete.png)

You will be redirected to the confirmation page and click on the `Yes, I'm sure` button.

![](./img/admin-maintenance-delete-confirm.png)

## Visit Flower Monitoring Tools

Go to the Django Admin Page and click on `Maintenances` tab.

![](./img/admin-maintenances-tab.png)

Click the `Visit Celery Flower` button to go to the task monitoring tools.

![](./img/admin-maintenances-flower.png)

![](./img/flower.png)

## How to Add GeoSight API Keys to Dataset Permissions 

Go to the dataset listing page and click on one of the datasets.

![](./img/gs-api-key-1.png)

Go to the Permission Tab then to the User tab and click on the `Add User` button.

![](./img/gs-api-key-2.png)

For a Level 4 API Key, select **API_KEY GeoSight_lv_4 (Viewer)** as the User, **Read** as the Permission, and a Privacy Level of **4 - Highly confidential**. Click on the `Save` button to add the permission.

![](./img/gs-api-key-3.png)

For a Level 1 API Key, select **API_KEY GeoSight_lv_1 (Viewer)** as the User, **Read** as the Permission, and a Privacy Level of **1 - Publicly shareable**. Click on the `Save` button to add the permission.

![](./img/gs-api-key-4.png)


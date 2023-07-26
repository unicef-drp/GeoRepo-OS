# GeoRepo API Format

## Endpoints

GeoRepo uses following restful URLs format for its endpoints:

Example:

```text
/api/{param1}/{param2}/{param3}/
```

API parameters are in the URL path instead of query parameters.

The benefit for this approach is that we can use dynamic parameters with its value in same endpoint.

E.g. we can query the geographical entity's bounding box with different id type as shown below:

```text
/api/dataset-entity/bbox/pcode/PAK/
/api/dataset-entity/bbox/id/12/
```

## Error Response

For every error response with status 40x or 500, GeoRepo will return detail error in JSON format.

Example:

```json
{
    'detail' : 'Invalid Parameter!'
}
```

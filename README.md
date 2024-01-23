# WEBPROJ

WEBPROJ is a REST API that exposes coordinate transformations for coordinate
reference systems in Denmark and Greenland. The production version of WEBPROJ
is running as part of [Dataforsyningen](https://dataforsyningen.dk). To use the API you
need an access token, which users of Dataforsyningen can generate when they are
logged in to their personal accounts. The documentation the REST API can be found
at https://docs.dataforsyningen.dk/#webproj.

## API

The API is a simple REST API that delivers data in JSON format. The two main
entry points are provided: `/crs/` and `/trans/`.

### Installation

For ease of installation it is recommended to setup an environment
using conda

```
$ conda env create -f environment.yaml
```

Replace `environment.yaml` with `environment-dev.yaml` if you want
to setup a development environment.

Activate the new environment with

```
$ conda activate webproj
```

Remember to run projsync in order to install the datum grids.

```
$ projsync --source-id dk_sdfe
$ projsync --source-id dk_sdfi
```

### Tests

WEBPROJ uses the `pytest` environment for tests. Run the test-suite with

```
$ pytest
```

in the root of the repository.

### Usage

For a simple demonstration of the WEBPROJ REST API a webserver can
be started locally by running

```
(webproj) C:\dev\webproj>uvicorn app.main:app --host 127.0.0.1 --port 8000
```

This will spawn a web-server that serves the API locally on
`http://127.0.0.1:8000/`.

The API exposes a small set of features that are accessed via URL
entry points. OpenAPI documentation is auto-generated and is available
in a user-friendly web UI at `/documentation`. A machine-readable version
of the same documentation is available at `/openapi.json`.

For version 1.0 of the API we have:

#### `/crs/`

Returns a list of available coordinate references systems that can
be transformed between.

##### Example

```
$ curl http://127.0.0.1:8000/v1.0/crs/
{
DK: [
    "EPSG:25832",
    "EPSG:4258"
],
GL: [
    "EPSG:3184",
    "EPSG:4909"
]
}
```

#### `/crs/<CRS>`

Returns information about a specific coordinate reference system.

##### Example

```
$curl http://127.0.0.1:8000/v1.0/crs/EPSG:25832
{
    country: "DK",
    title: "ETRS89 / UTM Zone 32 Nord",
    title_short: "ETRS89/UTM32N",
    v1: "Easting",
    v1_short: "x",
    v2: "Northing",
    v2_short: "y",
    v3: "kote",
    v3_short: "h",
    v4: null,
    v4_short: null
}
```

#### `/trans/<src_crs>/<dst_crs>/<coord>`

Transform coordinate `<coord>` from `<src_crs>` to `<dst_src`. Coordinate
input can be either 2D, 3D or 4D. The returned output will always be 4D, but
depending on the input the number of used output coordinate components varies.

##### Examples

```
# 2D
curl http://127.0.0.1:8000/v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0
{
    "v1:": 687071.4391094431,
    "v2": 6210141.326748009,
    "v3": 0.0,
    "v4": 0.0
}

# 3D
curl http://127.0.0.1:8000/v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0,30.0
{
    "v1:": 687071.4391094431,
    "v2": 6210141.326748009,
    "v3": 30.0,
    "v4": 0.0
}

# 4D
curl http://127.0.0.1:8000/v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0,30.0,2010.5
{
    "v1:": 687071.4391094431,
    "v2": 6210141.326748009,
    "v3": 30.0,
    "v4": 2010.5
}
```

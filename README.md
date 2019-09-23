# WEBPROJ

WEBPROJ is a proof-of-concept of a web API for exposing coordinate
transformations via PROJ. Eventually, the proof-of-concept will also
include a basic web application that consumes the API and makes
coordinate transformation simple for users who are not familiar with
PROJ and other professional GIS tools.

## API

The API is a simple REST API that delivers data in JSON format. In
the current version two main entry points are provided: `/crs/` and
`/trans/`.

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

For production use, the API should be installed as a component in a
WSGI compatible http server. How to configure this depends on the used http server.

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
(webproj) C:\dev\webproj>python webproj\api.py
```

This will spawn a Flask server that serves the API locally on
`http://127.0.0.1:5000/`.

The API exposes a small set of features that are accessed via URL
entry points. For version 1.0 of the API we have:

#### `/crs/`

Returns a list of available coordinate references systems that can
be transformed between.

##### Example

```
$ curl http://127.0.0.1:5000/v1.0/crs/
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
$curl http://127.0.0.1:5000/v1.0/crs/EPSG:25832
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
curl http://127.0.0.1:5000/v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0
{
    "v1:": 687071.4391094431,
    "v2": 6210141.326748009,
    "v3": 0.0,
    "v4": 0.0
}

# 3D
curl http://127.0.0.1:5000/v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0,30.0
{
    "v1:": 687071.4391094431,
    "v2": 6210141.326748009,
    "v3": 30.0,
    "v4": 0.0
}

# 4D
curl http://127.0.0.1:5000/v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0,30.0,2010.5
{
    "v1:": 687071.4391094431,
    "v2": 6210141.326748009,
    "v3": 30.0,
    "v4": 2010.5
}
```

## Web application

N/A.



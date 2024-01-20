from cmath import inf
import os
import json
from pathlib import Path
from typing import List, Tuple, Optional

from fastapi import (
    FastAPI,
    HTTPException,
    security,
    Depends,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pyproj
from pyproj.transformer import Transformer, AreaOfInterest

__VERSION__ = "1.2.3"

if "WEBPROJ_LIB" in os.environ:
    pyproj.datadir.append_data_dir(os.environ["WEBPROJ_LIB"])


# pylint: disable=unused-argument
def token_header_param(
    header_token: Optional[str] = Depends(
        security.api_key.APIKeyHeader(name="token", auto_error=False)
    ),
):
    """
    This defines an api-key header param named 'token

    Set auto_error to `True` to make `token `required.

    Function does absolutely nothing, hence the empty function body.
    The purpose of this function is to allow "token" to appear as
    an available header parameter in the auto-generated docs.
    The API Gateway on Dataforsyningen handles the token authentication
    so we don't actually have to do anything with the token value here.
    '"""


# pylint: disable=unused-argument
def token_query_param(
    query_token: Optional[str] = Depends(
        security.api_key.APIKeyQuery(name="token", auto_error=False)
    ),
):
    """
    This defines an api-key query param named 'token'

    Set auto_error to `True` to make `token `required.

    Function does absolutely nothing, hence the empty function body.
    The purpose of this function is to allow "token" to appear as
    an available query parameter in the auto-generated docs.
    The API Gateway on Dataforsyningen handles the token authentication
    so we don't actually have to do anything with the token value here.
    """


# Set up the app
app = FastAPI(
    title=__name__,
    description="## API til koordinattransformationer"
    "\n\n"
    "APIet __WEBPROJ__ giver adgang til at transformere "
    "multidimensionelle koordinatsæt. "
    "\n\n"
    "Til adgang benyttes Dataforsyningens brugeradgang som ved andre "
    "tjenester.",
    version=__VERSION__,
    terms_of_service="https://dataforsyningen.dk/Vilkaar",
    license="MIT License",
    license_url="https://raw.githubusercontent.com/SDFIdk/WEBPROJ/master/LICENSE",
    docs_url="/documentation",
    dependencies=[Depends(token_header_param), Depends(token_query_param)],
)
origins = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins)

_DATA = Path(__file__).parent / Path("data.json")

with open(_DATA, "r", encoding="UTF-8") as data:
    CRS_LIST = json.load(data)
    app.CRS_LIST = CRS_LIST

AOI = {
    "DK": AreaOfInterest(3.0, 54.5, 15.5, 58.0),
    "GL": AreaOfInterest(-75.0, 56.0, 8.5, 87.5),
}


def _make_4d(coord):
    if len(coord) == 2:
        return (coord[0], coord[1], None, None)

    if len(coord) == 3:
        return (coord[0], coord[1], coord[2], None)

    if len(coord) == 4:
        return (coord[0], coord[1], coord[2], coord[3])

    return ()


class OptimusPrime:
    """
    Optimus Prime is a Transformer... also, this is fun and avoids
    name clashes with pyproj
    """

    def __init__(self, src, dst):
        """
        Transformation from src to dst
        """
        self.pre_pipeline = None
        self.epsg_pipeline = None
        self.post_pipeline = None

        src = src.upper()
        dst = dst.upper()
        dst_hub = dst

        if src not in CRS_LIST.keys():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown source CRS identifier: '{src}'",
            )

        if dst not in CRS_LIST.keys():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Unknown destination CRS identifier: '{dst}'",
            )

        src_region = CRS_LIST[src]["country"]
        dst_region = CRS_LIST[dst]["country"]
        if src_region != dst_region and "Global" not in (src_region, dst_region):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="CRS's are not compatible across countries",
            )

        # determine region of transformation
        if src_region == dst_region:
            region = AOI[src_region]
        elif src_region == "Global":
            region = AOI[dst_region]
        else:
            region = AOI[src_region]

        src_auth = src.split(":")[0]
        dst_auth = dst.split(":")[0]

        # determine which transformation stops to do along the way
        non_epsg_src = src_auth != "EPSG"
        non_epsg_dst = dst_auth != "EPSG"

        if non_epsg_src:
            pipeline = (
                f"+proj=pipeline "
                f"+step +inv +init={src} "
                f"+step +proj=unitconvert +xy_in=rad +xy_out=deg "
                f"+step +proj=axisswap +order=2,1"
            )
            self.pre_pipeline = Transformer.from_pipeline(pipeline)

            if src_auth == "DK":
                src = "EPSG:4258"

        # standard case, which handles all transformations between
        # CRS's that are both EPSG SRID's AND which handles transformations
        # where ONE of the two CRS's is a non-EPSG SRID by supplying a
        # transformation hub using ETRS89 or GR96
        if src != dst or non_epsg_src != non_epsg_dst:
            if dst_auth == "DK":
                dst_hub = "EPSG:4258"
            if dst_auth == "GL":
                dst_hub = "EPSG:4909"

            try:
                self.epsg_pipeline = Transformer.from_crs(
                    src, dst_hub, area_of_interest=region
                )
            except RuntimeError as error:
                raise ValueError("Invalid CRS identifier") from error

        if non_epsg_dst:
            pipeline = (
                f"+proj=pipeline "
                f"+step +proj=axisswap +order=2,1 "
                f"+step +proj=unitconvert +xy_in=deg +xy_out=rad "
                f"+step +init={dst}"
            )
            self.post_pipeline = Transformer.from_pipeline(pipeline)

    def transform(self, coord):
        """
        Transform coordinate
        """
        (v1, v2, v3, v4) = coord
        if self.pre_pipeline:
            out = self.pre_pipeline.transform(v1, v2, v3, v4)
            (v1, v2, v3, v4) = _make_4d(out)

        if self.epsg_pipeline:
            out = self.epsg_pipeline.transform(v1, v2, v3, v4)
            (v1, v2, v3, v4) = _make_4d(out)

        if self.post_pipeline:
            out = self.post_pipeline.transform(v1, v2, v3, v4)
            (v1, v2, v3, v4) = _make_4d(out)

        if float("inf") in out or float("-inf") in out:
            raise HTTPException(
                status_code=404,
                detail="Input coordinate outside area of use of either source or destination CRS",
            )

        return (v1, v2, v3, v4)


class TransformerFactory:
    transformers = {}

    @classmethod
    def create(cls, src: str, dst: str):
        if src not in cls.transformers.keys():
            cls.transformers[src] = {}

        if dst not in cls.transformers[src].keys():
            cls.transformers[src][dst] = OptimusPrime(src, dst)

        return cls.transformers[src][dst]


# Set up return types


class CRSList(BaseModel):
    """Return response for List of CRS's"""

    DK: List[str]
    GL: List[str]
    Global: List[str]


class CRS_1_0(BaseModel):  # pylint: disable=invalid-name
    """Return response for CRS"""

    country: str
    title: str
    title_short: str
    v1: str
    v1_short: str
    v2: str
    v2_short: str
    v3: str | None
    v3_short: str | None
    v4: str | None
    v4_short: str | None


class CRS_1_1(CRS_1_0):  # pylint: disable=invalid-name
    """Return response for CRS"""

    srid: str
    area_of_use: str
    bounding_box: Tuple[float, float, float, float]


class CRS_1_2(CRS_1_1):  # pylint: disable=invalid-name
    """Return response for CRS"""

    v1_unit: str
    v2_unit: str
    v3_unit: str | None
    v4_unit: str | None


class Coordinate(BaseModel):
    """Return response of a coordinate"""

    v1: float
    v2: float
    v3: float | None
    v4: float | None


class HTTPError(BaseModel):
    """Return response in case of an error"""

    detail: str


class WEBPROJInfo(BaseModel):
    """Return response for WEBPROJ info"""

    webproj_version: str
    proj_version: str


# Set up API entry-points


@app.get("/v1.0/crs/")
@app.get("/v1.1/crs/")
@app.get("/v1.2/crs/")
def crs_index() -> CRSList:
    """
    List available coordinate reference systems
    """
    index = {}
    for srid, crsinfo in CRS_LIST.items():
        if crsinfo["country"] not in index:
            index[crsinfo["country"]] = []
        index[crsinfo["country"]].append(srid)

    return index


@app.get(
    "/v1.0/crs/{crs}",
    responses={
        status.HTTP_200_OK: {"model": CRS_1_0},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError},
    },
)
def crs_v1_0(crs):
    """
    Retrieve information about a given coordinate reference system
    """
    try:
        return CRS_LIST[crs.upper()]
    except KeyError:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"'{crs}' not available."
        )


@app.get(
    "/v1.1/crs/{crs}",
    responses={
        status.HTTP_200_OK: {"model": CRS_1_1},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError},
    },
)
def crs_v1_1(crs):
    """
    Retrieve information about a given coordinate reference system

    Version 1.1 includes the SRID, area of use and bounding box in
    the CRS info.
    """
    output = crs_v1_0(crs)
    if isinstance(output, HTTPException):
        # If we receive an error from crs_v1_0 we swiftly pass it on
        return output

    output["srid"] = crs

    # determine area of use and bounding box
    try:
        crs_from_db = pyproj.CRS.from_user_input(crs.upper())
        if crs_from_db.is_compound:
            area = inf
            for subcrs in crs_from_db.sub_crs_list:
                aou = subcrs.area_of_use
                bbox_area = aou.east - aou.west * aou.north - aou.south
                if bbox_area < area:
                    output["area_of_use"] = subcrs.area_of_use.name
                    output["bounding_box"] = list(subcrs.area_of_use.bounds)
        else:
            output["area_of_use"] = crs_from_db.area_of_use.name
            output["bounding_box"] = list(crs_from_db.area_of_use.bounds)
    except pyproj.exceptions.CRSError:
        # special cases not in proj.db
        if crs == "DK:S34J":
            output["area_of_use"] = "Denmark - Jutland onshore"
            output["bounding_box"] = [8.0, 54.5, 11.0, 57.75]
        elif crs == "DK:S34S":
            output["area_of_use"] = "Denmark - Sealand onshore"
            output["bounding_box"] = [11.0, 54.5, 12.8, 56.5]
        elif crs == "DK:S45B":
            output["area_of_use"] = "Denmark - Bornholm onshore"
            output["bounding_box"] = [14.6, 54.9, 15.2, 55.3]
        else:
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{crs}' not available.",
            )

    return output


@app.get(
    "/v1.2/crs/{crs}",
    responses={
        status.HTTP_200_OK: {"model": CRS_1_2},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError},
    },
)
def crs_v1_2(crs):
    """
    Retrieve information about a given coordinate reference system

    Version 1.2 includes coodinate units of the returned CRS.
    """
    output = crs_v1_1(crs)
    if isinstance(output, HTTPException):
        # If we receive an error from crs_v1_0 we swiftly pass it on
        return output

    # initialize unit elements in output dict
    for i in range(1, 5):
        output[f"v{i}_unit"] = None

    try:
        crs_from_db = pyproj.CRS.from_user_input(crs.upper())
        for i, axis in enumerate(crs_from_db.axis_info, start=1):
            output[f"v{i}_unit"] = axis.unit_name

    except pyproj.exceptions.CRSError:
        # special cases not in proj.db
        if crs == "DK:S34J":
            output["v1_unit"] = "metre"
            output["v2_unit"] = "metre"
        elif crs == "DK:S34S":
            output["v1_unit"] = "metre"
            output["v2_unit"] = "metre"
        elif crs == "DK:S45B":
            output["v1_unit"] = "metre"
            output["v2_unit"] = "metre"
        else:
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"'{crs}' not available"
            )

    # sort output for improved human readability
    return dict(sorted(output.items()))


@app.get("/v1.0/trans/{src}/{dst}/{v}")
@app.get("/v1.1/trans/{src}/{dst}/{v}")
@app.get("/v1.2/trans/{src}/{dst}/{v}")
async def transformation_2d(src: str, dst: str, v: str) -> Coordinate:
    """
    Transform a 2D coordinate from one CRS to another
    """

    try:
        v = v.split(",")
        if len(v) == 4:
            transformer = TransformerFactory.create(src, dst)
            (v1, v2, v3, v4) = transformer.transform(_make_4d((v[0], v[1], v[2], v[3])))
            return {"v1": v1, "v2": v2, "v3": v3, "v4": v4}
        elif len(v) == 3:
            transformer = TransformerFactory.create(src, dst)
            (v1, v2, v3, _) = transformer.transform(_make_4d((v[0], v[1], v[2])))
            return {"v1": v1, "v2": v2, "v3": v3, "v4": None}
        elif len(v) == 2:
            transformer = TransformerFactory.create(src, dst)
            (v1, v2, _, _) = transformer.transform(_make_4d((v[0], v[1])))
            return {"v1": v1, "v2": v2, "v3": None, "v4": None}
    except ValueError as error:
        return HTTPException(status_code=404, detail=error)


@app.get("/v1.0/trans/{src}/{dst}/{v1},{v2},{v3}")
@app.get("/v1.1/trans/{src}/{dst}/{v1},{v2},{v3}")
@app.get("/v1.2/trans/{src}/{dst}/{v1},{v2},{v3}")
async def transformation_3d(
    src: str, dst: str, v1: str, v2: str, v3: str
) -> Coordinate:
    """
    Transform a 3D coordinate from one CRS to another
    """
    try:
        transformer = TransformerFactory.create(src, dst)
        (v1, v2, v3, _) = transformer.transform(_make_4d((v1, v2, v3)))
    except ValueError as error:
        return HTTPException(status_code=404, detail=error)

    return {"v1": v1, "v2": v2, "v3": v3, "v4": None}


@app.get("/v1.0/trans/{src}/{dst}/{v1},{v2},{v3},{v4}")
@app.get("/v1.1/trans/{src}/{dst}/{v1},{v2},{v3},{v4}")
@app.get("/v1.2/trans/{src}/{dst}/{v1},{v2},{v3},{v4}")
async def transformation_4d(
    src: str, dst: str, v1: str, v2: str, v3: str, v4: str
) -> Coordinate:
    """
    Transform a 4D coordinate from one CRS to another
    """
    try:
        transformer = TransformerFactory.create(src, dst)
        (v1, v2, v3, v4) = transformer.transform((v1, v2, v3, v4))
    except ValueError as error:
        return HTTPException(status_code=404, detail=error)

    return {"v1": v1, "v2": v2, "v3": v3, "v4": v4}


@app.get("/v1.2/info")
async def info() -> WEBPROJInfo:
    """
    Retrieve information about the running instance of WEBPROJ and it's constituent components.
    """
    return {
        "webproj_version": __VERSION__,
        "proj_version": pyproj.__proj_version__,
    }

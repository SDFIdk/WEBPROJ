from cmath import inf
import os
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import pyproj
from pyproj.transformer import Transformer, AreaOfInterest

version = "1.2.0"

if "WEBPROJ_LIB" in os.environ:
    pyproj.datadir.append_data_dir(os.environ["WEBPROJ_LIB"])

# Set up the app
app = FastAPI(
    title=__name__,
    description="## API til koordinattransformationer"
    "\n\n"
    "APIet __WEBPROJ__ giver adgang til at transformere "
    "multidimensionelle koordinatsæt. "
    "\n\n"
    "Til adgang benyttes Dataforsyningens brugeradgang som ved andre "
    "tjenester."
    "\n\n"
    "[Versionshistorik](/webproj.txt)",
    version=version,
    terms_of_service="https://dataforsyningen.dk/Vilkaar",
    contact="support@sdfi.dk",
    license="MIT License",
    license_url="https://raw.githubusercontent.com/SDFIdk/WEBPROJ/master/LICENSE",
    docs_url="/documentation",
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
                status_code=400, detail=f"Unknown source CRS identifier: '{src}'"
            )

        if dst not in CRS_LIST.keys():
            raise HTTPException(
                status_code=400, detail=f"Unknown destination CRS identifier: '{dst}'"
            )

        src_region = CRS_LIST[src]["country"]
        dst_region = CRS_LIST[dst]["country"]
        if src_region != dst_region and "Global" not in (src_region, dst_region):
            raise HTTPException(
                status_code=400, detail="CRS's are not compatible across countries"
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
            except RuntimeError as e:
                raise ValueError("Invalid CRS identifier")

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


@app.get("/")
def Endpoint():
    return {}


@app.get("/v1.0/crs/")
@app.get("/v1.1/crs/")
@app.get("/v1.2/crs/")
def CRSIndex():
    """
    List available coordinate reference systems
    """
    index = {}
    for srid, crsinfo in CRS_LIST.items():
        if crsinfo["country"] not in index:
            index[crsinfo["country"]] = []
        index[crsinfo["country"]].append(srid)

    return index


@app.get("/v1.0/crs/{crs}")
def CRS(crs):
    """
    Retrieve information about a given coordinate reference system
    """
    try:
        return CRS_LIST[crs.upper()]
    except KeyError:
        return HTTPException(status_code=400, detail=f"'{crs}' not available.")


@app.get("/v1.1/crs/{crs}")
def CRSv1_1(crs):
    """
    Retrieve information about a given coordinate reference system

    Version 1.1 includes the SRID, area of use and bounding box in
    the CRS info.
    """
    output = CRS(crs)
    if type(output) == HTTPException:
        return HTTPException(status_code=400, detail=f"'{crs}' not available.")
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
            HTTPException(status_code=404, detail=f"'{crs}' not available")

    return output


@app.get("/v1.2/crs/{crs}")
def CRSv1_2(crs):
    """
    Retrieve information about a given coordinate reference system

    Version 1.2 includes coodinate units of the returned CRS.
    """
    output = CRSv1_1(crs)
    if type(output) == HTTPException:
        return HTTPException(status_code=400, detail=f"'{crs}' not available.")

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
            HTTPException(status_code=404, detail=f"'{crs}' not available")

    # sort output for improved human readability
    return dict(sorted(output.items()))


@app.get("/v1.0/trans/{src}/{dst}/{v}")
@app.get("/v1.1/trans/{src}/{dst}/{v}")
@app.get("/v1.2/trans/{src}/{dst}/{v}")
async def Transformation2D(src: str, dst: str, v: str):
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
            return {"v1": v1, "v2": v2, "v3": v3, "v4": 0.0}
        elif len(v) == 2:
            transformer = TransformerFactory.create(src, dst)
            (v1, v2, _, _) = transformer.transform(_make_4d((v[0], v[1])))
            return {"v1": v1, "v2": v2, "v3": 0.0, "v4": 0.0}
    except ValueError as error:
        HTTPException(status_code=404, detail=error)


# @app.get("/v1.0/trans/{src}/{dst}/{v1},{v2},{v3}")
# @app.get("/v1.1/trans/{src}/{dst}/{v1},{v2},{v3}")
# @app.get("/v1.2/trans/{src}/{dst}/{v1},{v2},{v3}")
# async def Transformation3D(src:str,dst:str,v1:str,v2:str,v3:str):
#     """
#     Transform a 3D coordinate from one CRS to another
#     """
#     try:
#         transformer = TransformerFactory.create(src, dst)
#         (v1, v2, v3, _) = transformer.transform(_make_4d((v1, v2, v3)))
#     except ValueError as error:
#         HTTPException(status_code=404,detail=error)

#     return {"v1": v1, "v2": v2, "v3": v3, "v4": 0.0}


# @app.get("/v1.0/trans/{src}/{dst}/{v1},{v2},{v3},{v4}")
# @app.get("/v1.1/trans/{src}/{dst}/{v1},{v2},{v3},{v4}")
# @app.get("/v1.2/trans/{src}/{dst}/{v1},{v2},{v3},{v4}")
# async def Transformation4D(src:str,dst:str,v1:str,v2:str,v3:str,v4:str):
#     """
#     Transform a 4D coordinate from one CRS to another
#     """
#     try:
#         transformer = TransformerFactory.create(src, dst)
#         (v1, v2, v3, v4) = transformer.transform((v1, v2, v3, v4))
#     except ValueError as error:
#         return HTTPException(status_code=404,detail=error)

#     return {"v1": v1, "v2": v2, "v3": v3, "v4": v4}


@app.get("/v1.2/info")
def Info():
    """
    Retrieve information about the running instance of WEBPROJ and it's constituent components.
    """
    return {
        "webproj_version": version,
        "proj_version": pyproj.__proj_version__,
    }


if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=5000, reload=True)

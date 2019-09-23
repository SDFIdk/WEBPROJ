import json
from pathlib import Path

from flask import Flask
from flask_restplus import Api, Resource, fields, abort
from pyproj.transformer import Transformer, AreaOfInterest


app = Flask(__name__)
api = Api(app)

_DATA = Path(__file__).parent / Path("data.json")

with open(_DATA, "r", encoding="UTF-8") as data:
    CRS_LIST = json.load(data)

AOI = {
    'DK': AreaOfInterest(3.0, 54.5, 15.5, 58.0),
    'GL': AreaOfInterest(-75.0, 56.0, 8.5, 87.5)
}

class EndPoint(Resource):
    def get(self):
        return {}


class CRSIndex(Resource):
    def get(self):
        """
        List available coordinate reference systems
        """
        index = {}
        for srid, crsinfo in CRS_LIST.items():
            if crsinfo["country"] not in index:
                index[crsinfo["country"]] = []
            index[crsinfo["country"]].append(srid)

        return index


class CRS(Resource):
    def get(self, crs):
        """
        Retrieve information about a given coordinate reference system
        """
        try:
            return CRS_LIST[crs.upper()]
        except KeyError:
            abort(404, message=f"'{crs}' not available")


class Transformation(Resource):

    def _make_4d(self, coord):

        if len(coord) == 2:
            return (coord[0], coord[1], None, None)

        if len(coord) == 3:
            return (coord[0], coord[1], coord[2], None)

        if len(coord) == 4:
            return (coord[0], coord[1], coord[2], coord[3])

        return ()

    @api.doc(params={
        'src': 'Source CRS',
        'dst': 'Destination CRS',
        'v1': '1st coordinate component',
        'v2': '2nd coordinate component',
        'v3': '3rd coordinate component',
        'v4': '4th coordinate component',
    })
    def get(self, src, dst, v1, v2, v3=None, v4=None):
        """
        Transform a coordinate from one CRS to another
        """
        src = src.upper()
        dst = dst.upper()
        dst_hub = dst

        if src not in CRS_LIST.keys():
            abort(404, message=f"Unknown source CRS identifier: '{src}'")

        if dst not in CRS_LIST.keys():
            abort(404, message=f"Unknown destination CRS identifier: '{dst}'")

        src_region = CRS_LIST[src]['country']
        dst_region = CRS_LIST[dst]['country']
        if src_region not in (dst_region, 'Global'):
            abort(404, message="CRS's are not compatible across countries")

        # determine region of transformation
        if src_region == dst_region:
            region = AOI[src_region]
        elif src_region == 'Global':
            region = AOI[dst_region]
        else:
            region = AOI[src_region]

        src_auth = src.split(':')[0]
        dst_auth = dst.split(':')[0]

        # determine which transformation stops to do along the way
        non_epsg_src = src_auth != 'EPSG'
        non_epsg_dst = dst_auth != 'EPSG'

        if non_epsg_src:
            pipeline = (f"+proj=pipeline "
                        f"+step +inv +init={src} "
                        f"+step +proj=unitconvert +xy_in=rad +xy_out=deg "
                        f"+step +proj=axisswap +order=2,1"
            )
            p = Transformer.from_pipeline(pipeline)
            out = p.transform(v1, v2, v3, v4)
            (v1, v2, v3, v4) = self._make_4d(out)

            if src_auth == 'DK':
                src = "EPSG:4258"

        # standard case, which handles all transformations between
        # CRS's that are both EPSG SRID's AND which handles transformations
        # where ONE of the two CRS's is a non-EPSG SRID by supplying a
        # transformation hub using ETRS89 or GR96
        if src != dst or non_epsg_src != non_epsg_dst:
            if dst_auth == 'DK':
                dst_hub = "EPSG:4258"
            if dst_auth == 'GL':
                dst_hub = "EPSG:4909"

            try:
                transformer = Transformer.from_crs(src, dst_hub, area_of_interest=region)
            except RuntimeError as e:
                print(e)
                abort(404, message="Invalid CRS identifier")

            out = transformer.transform(v1, v2, v3, v4)
            (v1, v2, v3, v4) = self._make_4d(out)

        if non_epsg_dst:
            pipeline = (f"+proj=pipeline "
                        f"+step +proj=axisswap +order=2,1 "
                        f"+step +proj=unitconvert +xy_in=deg +xy_out=rad "
                        f"+step +init={dst}"
            )
            p = Transformer.from_pipeline(pipeline)
            print(v1, v2, v3, v4)
            out = p.transform(v1, v2, v3, v4)
            (v1, v2, v3, v4) = self._make_4d(out)

        return {"v1": v1, "v2": v2, "v3": v3, "v4": v4}


api.add_resource(EndPoint, "/")
api.add_resource(CRSIndex, "/v1.0/crs/")
api.add_resource(CRS, "/v1.0/crs/<string:crs>")
api.add_resource(
    Transformation,
    "/v1.0/trans/<string:src>/<string:dst>/<float:v1>,<float:v2>",
    endpoint="trans_2d",
)
api.add_resource(
    Transformation,
    "/v1.0/trans/<string:src>/<string:dst>/<float:v1>,<float:v2>,<float:v3>",
    endpoint="trans_3d",
)
api.add_resource(
    Transformation,
    "/v1.0/trans/<string:src>/<string:dst>/<float:v1>,<float:v2>,<float:v3>,<float:v4>",
    endpoint="trans_4d",
)

if __name__ == "__main__":
    app.run(debug=True)

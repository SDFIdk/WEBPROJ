import json
from pathlib import Path

from flask import Flask
from flask_restful import Api, Resource, reqparse, abort
from flask_restful_swagger import swagger
import pyproj


app = Flask(__name__)
api = Api(app)

DATA = Path(__file__).parent / Path("data.json")

with open(DATA, "r", encoding="UTF-8") as data:
    CRS_LIST = json.load(data)

class EndPoint(Resource):
    def get(self):
        return {}


class CRSIndex(Resource):
    def get(self):
        index = {}
        for srid, crsinfo in CRS_LIST.items():
            if crsinfo["country"] not in index:
                index[crsinfo["country"]] = []
            index[crsinfo["country"]].append(srid)

        return index


class CRS(Resource):
    def get(self, crs):
        try:
            return CRS_LIST[crs.upper()]
        except KeyError:
            abort(404, message=f"'{crs}' not available")


class Transformation(Resource):
    def get(self, src, dst, v1, v2, v3=0.0, v4=0.0):
        src = src.upper()
        dst = dst.upper()
        try:
            pj_src = pyproj.Proj(f"+init={src}")
            pj_dst = pyproj.Proj(f"+init={dst}")

        except RuntimeError:
            abort(404, message="Invalid CRS identifier")

        out = pyproj.transform(pj_src, pj_dst, v1, v2, v3)

        return {"v1": out[0], "v2": out[1], "v3": out[2], "v4": v4}

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

import sys
import json
import unittest

from webproj import api


class WebProjTest(unittest.TestCase):
    def assert_result(self, entry, expected_json_output):
        """
        Check that a given API reource return the expected result
        """
        response = self.app.get(entry)
        self.assertEqual(
            json.loads(response.get_data().decode(sys.getdefaultencoding())),
            expected_json_output,
        )


class TestAPI(WebProjTest):
    def setup_class(self):
        self.app = api.app.test_client()

    def test_root(self):
        """
        Test that the root of the API returns something
        """
        self.assert_result("/", {})

    def test_crs_index(self):
        """
        Test that the index of all available CRS's is returned
        correctly.
        """
        expected = {}
        for srid, crsinfo in api.CRS_LIST.items():
            if crsinfo["country"] not in expected:
                expected[crsinfo["country"]] = []
            expected[crsinfo["country"]].append(srid)

        self.assert_result("/v1.0/crs/", expected)

    def test_crs(self):
        """
        Test that CRS descriptions are presented correctly
        """
        for srid, crsinfo in api.CRS_LIST.items():
            self.assert_result(f"/v1.0/crs/{srid}", crsinfo)

    def test_crs_that_doesnt_exist(self):
        """
        Test that we get the proper response when requesting an unknown CRS
        """
        expected = {"message": "'unknowncrs' not available"}

        self.assert_result("/v1.0/crs/unknowncrs", expected)

    def test_trans_2d(self):
        """
        Test that 2D transformations behaves as expected
        """
        api_entry = "/v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0"
        expected = {
            "v1": 687071.4391094431,
            "v2": 6210141.326748009,
            "v3": 0.0,
            "v4": 0.0,
        }
        self.assert_result(api_entry, expected)

    def test_trans_3d(self):
        """
        Test that 3D transformations behaves as expected
        """
        api_entry = "/v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0,30.0"
        expected = {
            "v1": 687071.4391094431,
            "v2": 6210141.326748009,
            "v3": 30.0,
            "v4": 0.0,
        }
        self.assert_result(api_entry, expected)

    def test_trans_4d(self):
        """
        Test that 4D transformations behaves as expected
        """
        api_entry = "/v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0,30.0,2010.5"
        expected = {
            "v1": 687071.4391094431,
            "v2": 6210141.326748009,
            "v3": 30.0,
            "v4": 2010.5,
        }
        self.assert_result(api_entry, expected)

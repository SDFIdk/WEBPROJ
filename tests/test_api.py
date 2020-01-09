import sys
import json
import unittest

from webproj import api


class WebProjTest(unittest.TestCase):
    def assert_result(self, entry, expected_json_output):
        """
        Check that a given API resource return the expected result.
        """
        response = self.app.get(entry)
        self.assertEqual(
            json.loads(response.get_data().decode(sys.getdefaultencoding())),
            expected_json_output,
        )

    def assert_coordinate(self, entry, expected_json_output, tolerance=1e-6):
        """
        Check that a returned coordinate matches the expected result
        within a pre-determined tolerance
        """
        response = self.app.get(entry)
        result = json.loads(response.get_data().decode(sys.getdefaultencoding()))
        for key in expected_json_output.keys():
            if not key in result.keys():
                raise AssertionError

        for key, value in result.items():
            expected_value = expected_json_output[key]
            if value is  None and expected_value is None:
                continue
            if abs(value - expected_value) > tolerance:
                raise AssertionError


class TestAPI(WebProjTest):
    def setup_class(self):
        self.app = api.app.test_client()

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
        expected = {
            "message": "'unknowncrs' not available. You have requested this URI [/v1.0/crs/unknowncrs] but did you mean /v1.0/crs/<string:crs> ?"
        }

        self.assert_result("/v1.0/crs/unknowncrs", expected)

    def test_transformer_caching(self):
        """
        Check that caching works by comparing objects with the is operator
        """

        transformer_a = api.TransformerFactory.create("EPSG:4095", "EPSG:4096")
        transformer_b = api.TransformerFactory.create("EPSG:4095", "EPSG:4096")

        assert transformer_a is transformer_b

    def test_trans_2d(self):
        """
        Test that 2D transformations behaves as expected
        """
        api_entry = "/v1.0/trans/EPSG:4258/EPSG:25832/56.0,12.0"
        expected = {
            "v1": 687071.4391094431,
            "v2": 6210141.326748009,
            "v3": None,
            "v4": None,
        }
        self.assert_coordinate(api_entry, expected)

    def test_trans_3d(self):
        """
        Test that 3D transformations behaves as expected
        """
        api_entry = "/v1.0/trans/EPSG:4258/EPSG:25832/56.0,12.0,30.0"
        expected = {
            "v1": 687071.4391094431,
            "v2": 6210141.326748009,
            "v3": 30.0,
            "v4": None,
        }
        self.assert_coordinate(api_entry, expected)

    def test_trans_4d(self):
        """
        Test that 4D transformations behaves as expected
        """
        api_entry = "/v1.0/trans/EPSG:4258/EPSG:25832/56.0,12.0,30.0,2010.5"
        expected = {
            "v1": 687071.4391094431,
            "v2": 6210141.326748009,
            "v3": 30.0,
            "v4": 2010.5,
        }
        self.assert_coordinate(api_entry, expected)

    def test_sys34(self):
        """
        Test that system 34 is handled correctly. In this case
        we transform from S34J to EPSG:25832 and vice versa.
        """
        api_entry_fwd = "v1.0/trans/DK:S34J/EPSG:25832/295799.3977,175252.0903"
        exp_fwd = {
            "v1": 499999.99999808666,
            "v2": 6206079.587029327,
            "v3": None,
            "v4": None,
        }
        self.assert_coordinate(api_entry_fwd, exp_fwd)

        api_entry_inv = "v1.0/trans/EPSG:25832/DK:S34J/500000.0,6205000.0"
        exp_inv = {
            "v1": 295820.9708249467,
            "v2": 174172.32360956355,
            "v3": None,
            "v4": None,
        }
        self.assert_coordinate(api_entry_inv, exp_inv)

        api_entry_js = (
            "v1.0/trans/DK:S34J/DK:S34S/138040.74248674404,63621.728972878314"
        )
        exp_js = {
            "v1": 138010.86611871765,
            "v2": 63644.234364821285,
            "v3": None,
            "v4": None,
        }
        self.assert_coordinate(api_entry_js, exp_js)

    def test_transformation_outside_crs_area_of_use(self):
        """
        Test that 404 is returned when a transformation can't return sane
        values due to usage outside defined area of use.
        """
        api_entry = "v1.0/trans/EPSG:4258/DK:S34S/12.0,56.0"
        expected = {
            "message": "Input coordinate outside area of use of either source or destination CRS"
        }
        self.assert_result(api_entry, expected)

    def test_negative_coordinate_values(self):
        """
        Negative coordinate values are occasionally needed, for instance
        longitudes in Greenland. Let's test that we can deal with them.
        """
        api_entry = "v1.0/trans/EPSG:4326/EPSG:25832/-12.0,56.0"
        expected = {
            "v1": 6231950.538290203,
            "v2": -1920310.7126844588,
            "v3": None,
            "v4": None,
        }
        self.assert_coordinate(api_entry, expected)

    def test_transformation_between_global_and_regional_crs(self):
        """
        Transformation between WGS84 and ETRS89/GR96 should be
        possible both ways. Test the logic that determines if two
        CRS's are compatible.
        """
        # first test the case from a global CRS to a regional CRS
        api_entry = (
            "/v1.0/trans/EPSG:4326/EPSG:25832/55.68950140789923,12.58696909994519"
        )
        expected = {"v1": 725448.0, "v2": 6177354.999999999, "v3": None, "v4": None}
        self.assert_coordinate(api_entry, expected)

        # then test the reverse case from regional to global
        api_entry = "/v1.0/trans/EPSG:25832/EPSG:4258/725448.0,6177355.0"
        expected = {
            "v1": 55.689501407899236,
            "v2": 12.58696909994519,
            "v3": None,
            "v4": None,
        }
        self.assert_coordinate(api_entry, expected, tolerance=1e-9)

        # test some failing cases DK -> GL
        api_entry = "v1.0/trans/EPSG:4258/EPSG:4909/55.0,12.0"
        expected = {"message": "CRS's are not compatible across countries"}
        self.assert_result(api_entry, expected)

        api_entry = "v1.0/trans/EPSG:4909/EPSG:4258/75.0,-50.0"
        expected = {"message": "CRS's are not compatible across countries"}
        self.assert_result(api_entry, expected)

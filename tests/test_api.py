import re
import pprint

import pytest
from fastapi.testclient import TestClient

from webproj.api import app, TransformerFactory


def _get_and_decode_response(entry):
    """
    Retrieves response from API and decodes the JSON data into a dict
    """
    client = TestClient(app)
    response = client.get(entry)
    decoded_response = response.json()
    return decoded_response


def _assert_result(entry, expected_json_output):
    """
    Check that a given API resource return the expected result.
    """
    print(entry)
    decoded_response = _get_and_decode_response(entry)
    pprint.pprint(decoded_response)
    print("-----")
    pprint.pprint(expected_json_output)
    assert decoded_response == expected_json_output


def _assert_key_value_set(entry, expected_key_value_set):
    """
    Check that a returned response contains the expected key
    value set
    """
    print(entry)
    decoded_response = _get_and_decode_response(entry)
    pprint.pprint(decoded_response)
    print("-----")
    pprint.pprint(expected_key_value_set)
    for key in expected_key_value_set.keys():
        if key not in decoded_response.keys():
            raise AssertionError

    for key, value in expected_key_value_set.items():
        assert decoded_response[key] == value


def _assert_coordinate(entry, expected_json_output, tolerance=1e-6):
    """
    Check that a returned coordinate matches the expected result
    within a pre-determined tolerance
    """
    client = TestClient(app)
    response = client.get(entry)
    result = response.json()
    print(expected_json_output)
    print(result)
    for key in expected_json_output.keys():
        if key not in result.keys():
            raise AssertionError

    for key, value in result.items():
        expected_value = expected_json_output[key]
        if value is None and expected_value is None:
            continue
        if abs(value - expected_value) > tolerance:
            raise AssertionError


@pytest.fixture(scope="module", params=["v1.0", "v1.1", "v1.2"])
def api_all(request):
    return request.param


@pytest.fixture(scope="module", params=["v1.1", "v1.2"])
def api_from_v1_1(request):
    return request.param


@pytest.fixture(scope="module", params=["v1.2"])
def api_from_v1_2(request):
    return request.param


def test_transformer_caching():
    """
    Check that caching works by comparing objects with the is operator
    """

    transformer_a = TransformerFactory.create("EPSG:4095", "EPSG:4096")
    transformer_b = TransformerFactory.create("EPSG:4095", "EPSG:4096")

    assert transformer_a is transformer_b


def test_crs(api_all):
    """
    Test that CRS descriptions are presented correctly
    """
    for srid, crsinfo in app.CRS_LIST.items():
        _assert_result(f"/{api_all}/crs/{srid}", crsinfo)


def test_crs_index(api_all):
    """
    Test that the index of all available CRS's is returned
    correctly.
    """
    expected = {}
    for srid, crsinfo in app.CRS_LIST.items():
        if crsinfo["country"] not in expected:
            expected[crsinfo["country"]] = []
        expected[crsinfo["country"]].append(srid)

    _assert_result(f"/{api_all}/crs/", expected)


def test_crs_that_doesnt_exist(api_all):
    """
    Test that we get the proper response when requesting an unknown CRS
    """
    response = _get_and_decode_response(f"/{api_all}/crs/unknowncrs")
    assert response['detail'] == "'unknowncrs' not available."


def test_trans_2d(api_all):
    """
    Test that 2D transformations behaves as expected
    """
    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56.0/12.0"
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)


def test_trans_3d(api_all):
    """
    Test that 3D transformations behaves as expected
    """
    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56.0/12.0/30.0"
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": 30.0,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)


def test_trans_4d(api_all):
    """
    Test that 4D transformations behaves as expected
    """
    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56.0/12.0/30.0/2010.5"
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": 30.0,
        "v4": 2010.5,
    }
    _assert_coordinate(api_entry, expected)


def test_sys34(api_all):
    """
    Test that system 34 is handled correctly. In this case
    we transform from S34J to EPSG:25832 and vice versa.
    """
    api_entry_fwd = f"/{api_all}/trans/DK:S34J/EPSG:25832/295799.3977/175252.0903"
    exp_fwd = {
        "v1": 499999.99999808666,
        "v2": 6206079.587029327,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry_fwd, exp_fwd)

    api_entry_inv = f"/{api_all}/trans/EPSG:25832/DK:S34J/500000.0/6205000.0"
    exp_inv = {
        "v1": 295820.9708249467,
        "v2": 174172.32360956355,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry_inv, exp_inv)

    api_entry_js = (
        f"/{api_all}/trans/DK:S34J/DK:S34S/138040.74248674404/63621.728972878314"
    )
    exp_js = {
        "v1": 138010.86611871765,
        "v2": 63644.234364821285,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry_js, exp_js)


def test_transformation_outside_crs_area_of_use(api_all):
    """
    Test that 404 is returned when a transformation can't return sane
    values due to usage outside defined area of use.
    """
    api_entry = f"/{api_all}/trans/EPSG:4258/DK:S34S/12.0/56.0"
    expected = {
        "detail": "Input coordinate outside area of use of either source or destination CRS"
    }
    _assert_result(api_entry, expected)


def test_negative_coordinate_values(api_all):
    """
    Negative coordinate values are occasionally needed, for instance
    longitudes in Greenland. Let's test that we can deal with them.
    """
    api_entry = f"/{api_all}/trans/EPSG:4326/EPSG:25832/-12.0/56.0"
    expected = {
        "v1": 6231950.538290203,
        "v2": -1920310.7126844588,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)


def test_transformation_between_global_and_regional_crs(api_all):
    """
    Transformation between WGS84 and ETRS89/GR96 should be
    possible both ways. Test the logic that determines if two
    CRS's are compatible.
    """
    # first test the case from a global CRS to a regional CRS
    api_entry = (
        f"/{api_all}/trans/EPSG:4326/EPSG:25832/55.68950140789923/12.58696909994519"
    )
    expected = {"v1": 725448.0, "v2": 6177354.999999999, "v3": None, "v4": None}
    _assert_coordinate(api_entry, expected)

    # then test the reverse case from regional to global
    api_entry = f"/{api_all}/trans/EPSG:25832/EPSG:4258/725448.0/6177355.0"
    expected = {
        "v1": 55.689501407899236,
        "v2": 12.58696909994519,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected, tolerance=1e-9)

    # test some failing cases DK -> GL
    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:4909/55.0/12.0"
    expected = {"detail": "CRS's are not compatible across countries"}
    _assert_result(api_entry, expected)

    api_entry = f"/{api_all}/trans/EPSG:4909/EPSG:4258/75.0/-50.0"
    expected = {"detail": "CRS's are not compatible across countries"}
    _assert_result(api_entry, expected)


def test_integer_coordinates(api_all):
    """
    Test the 'number' Werkzeug converter for parsing coordinates in routes
    """
    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56/12"
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)

    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56./12."
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)

    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56.0/12.0"
    expected = {
        "v1": 687071.4391094431,
        "v2": 6210141.326748009,
        "v3": None,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected)

    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56/12/0"
    expected = {"v1": 687071.4391094431, "v2": 6210141.326748009, "v3": 0.0, "v4": None}
    _assert_coordinate(api_entry, expected)

    api_entry = f"/{api_all}/trans/EPSG:4258/EPSG:25832/56/12/0/2020"
    expected = {"v1": 687071.4391094431, "v2": 6210141.326748009, "v3": 0.0, "v4": 2020}
    _assert_coordinate(api_entry, expected)


def test_combined_epsg_codes(api_all):
    """
    Test that EPSG codes that consist of a combination of two
    codes (horizontal+vertical) works as expected
    """
    api_entry = f"/{api_all}/trans/EPSG:4909/EPSG:3184+8267/64.0/-51.5/0"
    expected = {
        "v1": -108394.69573,
        "v2": 7156992.58360,
        "v3": -27.91300,
        "v4": None,
    }
    _assert_coordinate(api_entry, expected, tolerance=0.01)


def test_crs_return_srid(api_from_v1_1):
    """
    Test that CRS routes return the calling srid
    """
    testdata = {
        "EPSG:25832": {
            "srid": "EPSG:25832",
        },
        "EPSG:23032+5733": {
            "srid": "EPSG:23032+5733",
        },
        "DK:S34S": {
            "srid": "DK:S34S",
        },
    }

    for srid, crsinfo in testdata.items():
        api_entry = f"/{api_from_v1_1}/crs/{srid}"
        _assert_key_value_set(api_entry, crsinfo)


def test_crs_units(api_from_v1_2):
    """
    Test that CRS routes return the CRS axis units.
    """
    testdata = {
        "EPSG:25832": {
            "v1_unit": "metre",
            "v2_unit": "metre",
            "v3_unit": None,
            "v4_unit": None,
        },
        "EPSG:23032+5733": {
            "v1_unit": "metre",
            "v2_unit": "metre",
            "v3_unit": "metre",
            "v4_unit": None,
        },
        "DK:S34S": {
            "v1_unit": "metre",
            "v2_unit": "metre",
            "v3_unit": None,
            "v4_unit": None,
        },
    }

    for srid, crsinfo in testdata.items():
        api_entry = f"/{api_from_v1_2}/crs/{srid}"
        _assert_key_value_set(api_entry, crsinfo)


def test_info(api_from_v1_2):
    """
    Test that the info entrypoint returns sensible values.
    """
    response = _get_and_decode_response(f"/{api_from_v1_2}/info/")

    for software, version_number in response.items():
        print(software, version_number)
        assert re.match(r"^\d+\.\d+\.\d+$", version_number)

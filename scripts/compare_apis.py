"""
Script for comparing API deployed in test and prod.

The old Flask-based API includes whitespace and trailing newline in the response.
We knowingly strip that for the sake of comparison. If this affects users, they're
parsing the data in a bad way.
If necessary, the old ways can be introduced in FastAPI as well using a response_class.

For more, see:
https://stackoverflow.com/questions/67783530/is-there-a-way-to-pretty-print-prettify-a-json-response-in-fastapi
"""
import json

import requests

TOKEN = "<INSER TOKEN HERE>"

URL_TEST = "https://api.dataforsyningen.dk/rest/webproj_test/"
URL_PROD = "https://api.dataforsyningen.dk/rest/webproj/"

TEST_CASES = [
    "v1.0/crs/",
    "v1.1/crs/",
    "v1.2/crs/",

    "v1.0/crs/EPSG:4093",
    "v1.1/crs/EPSG:4093",
    "v1.2/crs/EPSG:4093",

    "v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0",
    "v1.1/trans/EPSG:4258/EPSG:25832/12.0,56.0",
    "v1.2/trans/EPSG:4258/EPSG:25832/12.0,56.0",

    "v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0,123.4",
    "v1.1/trans/EPSG:4258/EPSG:25832/12.0,56.0,123.4",
    "v1.2/trans/EPSG:4258/EPSG:25832/12.0,56.0,123.4",

    "v1.0/trans/EPSG:4258/EPSG:25832/12.0,56.0,123.4,2024.5",
    "v1.1/trans/EPSG:4258/EPSG:25832/12.0,56.0,123.4,2024.5",
    "v1.2/trans/EPSG:4258/EPSG:25832/12.0,56.0,123.4,2024.5",

    "v1.0/trans/EPSG:4230/DK:S34S/55.5190,11.83303",
    "v1.1/trans/EPSG:4230/DK:S34S/55.5190,11.83303",
    "v1.2/trans/EPSG:4230/DK:S34S/55.5190,11.83303",
]

EXPECTED_FAILURES = [
    # Different version numbers of both PROJ and WEBPROJ
    "v1.2/info/",
    "v1.2/info",

    # Area of use and bounding box are different due to changes in EPSG registry
    "v1.0/crs/EPSG:25832",
    "v1.1/crs/EPSG:25832",
    "v1.2/crs/EPSG:25832",

    # Numerical differences in the vertical component at the centimeter level.
    # Caused by use of different DVR90 geoid models in different PROJ versions
    # in PROD and TEST
    "v1.0/trans/EPSG:4258+5799/EPSG:4230+5733/55.6581,11.5991,52.4",
    "v1.1/trans/EPSG:4258+5799/EPSG:4230+5733/55.6581,11.5991,52.4",
    "v1.2/trans/EPSG:4258+5799/EPSG:4230+5733/55.6581,11.5991,52.4",
 ]

def run_test_case(test_case: str) -> bool:
    """
    Perform a specific test case.
    """
    r_test = requests.get(URL_TEST + test_case, params={"token": TOKEN})
    r_prod = requests.get(URL_PROD + test_case, params={"token": TOKEN})

    try:
        json_test = r_test.json()
    except json.decoder.JSONDecodeError:
        json_prod = "JSON decoding error"

    try:
        json_prod = r_prod.json()
    except json.decoder.JSONDecodeError:
        json_prod = "JSON decoding error"

    test_result = json_test == json_prod

    print(f"{test_case} {(test_result)}")

    if not test_result:
        print("-"*25)
        print(json_prod)
        print("")
        print(json_test)
        print("-"*25)

    return test_result

if __name__ == "__main__":
    for test_case in TEST_CASES:
        run_test_case(test_case)

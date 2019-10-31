"""
Helper modules for Fake MyTardis server
"""
import json
import logging
import os
import re
import sys
import tempfile

from ...utils.openssh import GetCygwinPath

logger = logging.getLogger(__name__)

TASTYPIE_CANNED_ERROR = {
    "error_message":
    "Sorry, this request could not be processed. Please try again later."
}

EMPTY_API_LIST = {
    "meta": {
        "limit": 20,
        "next": None,
        "offset": 0,
        "previous": None,
        "total_count": 0
    },
    "objects": []
}

with tempfile.NamedTemporaryFile() as tempFile:
    STAGING_PATH = tempFile.name
os.makedirs(STAGING_PATH)
logger.info("Created temporary staging directory: %s",
            STAGING_PATH)
if sys.platform.startswith("win"):
    STAGING_PATH = GetCygwinPath(STAGING_PATH)

TEST_FACILITY = {
    "id": 2,
    "manager_group": {
        "id": 2,
        "name": "test_facility_managers",
        "resource_uri": "/api/v1/group/2/"
    },
    "name": "Test Facility",
    "resource_uri": "/api/v1/facility/2/"
}

TEST_INSTRUMENT = {
    "facility": TEST_FACILITY,
    "id": 17,
    "name": "Test Instrument",
    "resource_uri": "/api/v1/instrument/17/"
}


def RespondWithStatusCode(mytardis, status, errorMessage=None):
    """
    Respond with status code and include an error message if supplied

    :param mytardis: The FakeMyTardisHandler instance
    """
    mytardis.send_response(status)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    if errorMessage:
        errorJson = dict(error_message=errorMessage)
    else:
        errorJson = TASTYPIE_CANNED_ERROR
    if errorMessage or status == 500:
        mytardis.wfile.write(json.dumps(errorJson).encode())


def RespondToRequestForStatusCode(mytardis):
    """
    Respond to a request for an HTTP status code.
    This is useful to test exception handling.

    :param mytardis: The FakeMyTardisHandler instance
    """
    match = re.match(r"^/request/http/code/(\d+)/.*$", mytardis.path)
    RespondWithStatusCode(mytardis, int(match.groups()[0]))

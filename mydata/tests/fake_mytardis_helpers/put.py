"""
mydata/tests/fake_mytardis_helpers/put.py

Responses to PUT requests for our fake MyTardis server
"""
import copy
import re
import json

from . import EMPTY_API_LIST, TASTYPIE_CANNED_ERROR
from . import TEST_FACILITY, TEST_INSTRUMENT


def FakeMyTardisPut(mytardis):
    """
    Respond to a PUT request.

    :param mytardis: The FakeMyTardisHandler instance
    """
    if mytardis.path.startswith("/request/http/code/"):
        match = re.match(r"^/request/http/code/(\d+)/.*$", mytardis.path)
        if match:
            httpCode = int(match.groups()[0])
        else:
            httpCode = 500
        mytardis.send_response(httpCode)
        mytardis.send_header("Content-type", "application/json")
        mytardis.end_headers()
        mytardis.wfile.write(json.dumps(TASTYPIE_CANNED_ERROR).encode())
        return

    if mytardis.path.startswith("/api/v1/mydata_uploader/"):
        match = re.match(r"^/api/v1/mydata_uploader/(\S+)/$", mytardis.path)
        uploaderId = match.groups()[0]
        mytardis.send_response(200)
        mytardis.send_header("Content-type", "application/json")
        mytardis.end_headers()
        uploaderJson = {
            "id": uploaderId,
            "name": "Test Instrument",
            "instruments": [TEST_INSTRUMENT],
            "resource_uri": "/api/v1/mydata_uploader/25/",
        }
        mytardis.wfile.write(json.dumps(uploaderJson).encode())
    elif mytardis.path.startswith("/api/v1/instrument/17/"):
        mytardis.send_response(200)
        mytardis.send_header("Content-type", "application/json")
        mytardis.end_headers()
        instrumentsJson = copy.deepcopy(EMPTY_API_LIST)
        instrumentsJson['meta']['total_count'] = 1
        instrumentsJson['objects'] = [
            {
                "id": 31,
                "name": "Renamed Instrument",
                "facility": TEST_FACILITY,
                "resource_uri": "/api/v1/instrument/17/"
            }
        ]
        mytardis.wfile.write(json.dumps(instrumentsJson).encode())
    else:
        raise Exception("FakeMyTardis Server doesn't know how to respond "
                        "to PUT: %s" % mytardis.path)

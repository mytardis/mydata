"""
mydata/tests/fake_mytardis_helpers/post.py

Responses to POST requests for our fake MyTardis server
"""
# pylint: disable=comparison-with-callable
import re
import json
import cgi

import six

from . import STAGING_PATH, TASTYPIE_CANNED_ERROR, TEST_FACILITY
from . import RespondToRequestForStatusCode, RespondWithStatusCode


def FakeMyTardisPost(mytardis):
    """
    Respond to a POST request

    :param mytardis: The FakeMyTardisHandler instance
    """
    if mytardis.path.startswith("/request/http/code/"):
        RespondToRequestForStatusCode(mytardis)
        return

    if mytardis.path.startswith("/request/connectionerror/"):
        mytardis.server.server_close()
        return

    assert mytardis.path.startswith("/api/v1/")
    authorization = mytardis.headers.get("Authorization", "")
    match = re.match(r"^ApiKey (\S+):(\S+)$", authorization)
    apiUsername = match.groups()[0]
    apiKey = match.groups()[1]
    if apiKey == "invalid":
        RespondWithStatusCode(mytardis, 401)
        return

    try:
        length = int(mytardis.headers['Content-Length'])
        contentType, _ = \
            cgi.parse_header(mytardis.headers.get('content-type'))
        if contentType == 'multipart/form-data':
            form = \
                cgi.FieldStorage(
                    fp=mytardis.rfile, headers=mytardis.headers,
                    environ={'REQUEST_METHOD': 'POST',
                             'CONTENT_TYPE': mytardis.headers['Content-Type']})
            postData = form['json_data']
        else:
            postData = json.loads(mytardis.rfile.read(length))
    except KeyError:
        mytardis.send_response(500)
        mytardis.send_header("Content-type", "application/json")
        mytardis.end_headers()
        mytardis.wfile.write(json.dumps(TASTYPIE_CANNED_ERROR).encode())
        return

    responderForPath = {
        "/api/v1/mydata_dataset_file/": RespondToDataFileRequest,
        "/api/v1/dataset_file/": RespondToDataFileRequest,
        "/api/v1/mydata_experiment/": RespondToExperimentRequest,
        "/api/v1/objectacl/": RespondToObjectAclRequest,
        "/api/v1/dataset/": RespondToDatasetRequest,
        "/api/v1/instrument/": RespondToInstrumentRequest,
        "/api/v1/mydata_uploaderregistrationrequest/":
            RespondToUploaderRegRequest
    }

    for path, responder in six.iteritems(responderForPath):
        if mytardis.path == path:
            if responder == RespondToDataFileRequest:
                responder(mytardis, postData, contentType)
            elif responder == RespondToObjectAclRequest:
                responder(mytardis, apiUsername)
            else:
                responder(mytardis, postData)
            return

    raise Exception("FakeMyTardis Server doesn't know how to respond "
                    "to POST: %s" % mytardis.path)


def RespondToDataFileRequest(mytardis, postData, contentType):
    """
    Respond to an datafile-related request.

    :param mytardis: The FakeMyTardisHandler instance
    :param postData: The POST data dict
    """
    mytardis.send_response(201)
    mytardis.send_header("Content-type", "text/html")
    mytardis.datafileIdAutoIncrement += 1
    mytardis.send_header("location",
                         "/api/v1/dataset_file/%d/"
                         % mytardis.datafileIdAutoIncrement)
    mytardis.end_headers()

    if contentType == 'multipart/form-data':
        return

    filename = postData['filename']
    directory = postData['directory']
    dataset = postData['dataset']  # e.g. "/api/v1/dataset/123/"
    datasetId = dataset.split("/")[-2]
    foundAttachedFile = ('attached_file' in postData)
    foundReplicas = ('replicas' in postData)
    # For datafiles uploaded via staging, the
    # POST request should return a temp url.
    if not foundReplicas and not foundAttachedFile:
        if directory and directory != "":
            tempUrl = "%s/DatasetDescription-%s/%s/%s" \
                % (STAGING_PATH, datasetId, directory, filename)
        else:
            tempUrl = "%s/DatasetDescription-%s/%s" \
                % (STAGING_PATH, datasetId, filename)
        mytardis.wfile.write(tempUrl.encode())


def RespondToExperimentRequest(mytardis, postData):
    """
    Respond to an experiment-related request.

    :param mytardis: The FakeMyTardisHandler instance
    :param postData: The POST data dict
    """
    if "Request 404 from Fake MyTardis Server" in postData['title']:
        mytardis.send_response(404)
        mytardis.send_header("Content-type", "text/html")
        mytardis.end_headers()
        errorJson = TASTYPIE_CANNED_ERROR
        mytardis.wfile.write(json.dumps(errorJson).encode())
        return
    mytardis.send_response(201)
    mytardis.send_header("Content-type", "text/html")
    mytardis.end_headers()
    experimentJson = {
        "approved": False,
        "authors": [],
        "created_by": "/api/v1/user/7/",
        "created_time": "2015-10-06T10:12:43.069846",
        "description": postData['description'],
        "end_time": None,
        "handle": "",
        "id": 2551,
        "institution_name": "Monash University",
        "locked": False,
        "owner_ids": [7, 149],
        "parameter_sets": [
            {
                "experiment": "/api/v1/experiment/2551/",
                "id": 2538,
                "parameters": [
                    {
                        "datetime_value": None,
                        "id": 5234,
                        "link_id": 25,
                        "name": "/api/v1/parametername/309/",
                        "numerical_value": None,
                        "parameterset": "/api/v1/experimentparameterset/2538/",
                        "resource_uri": "/api/v1/experimentparameter/5234/",
                        "string_value": "cfb48c4f-29cc-11e5-b8ee-a45e60d72633",
                        "value": None
                    },
                    {
                        "datetime_value": None,
                        "id": 5235,
                        "link_id": None,
                        "name": "/api/v1/parametername/310/",
                        "numerical_value": None,
                        "parameterset": "/api/v1/experimentparameterset/2538/",
                        "resource_uri": "/api/v1/experimentparameter/5235/",
                        "string_value": "testuser2",
                        "value": None
                    }
                ],
                "resource_uri": "/api/v1/experimentparameterset/2538/",
                "schema": {
                    "hidden": True,
                    "id": 31,
                    "immutable": True,
                    "name": "MyData Default Experiment",
                    "namespace":
                        "http://mytardis.org"
                        "/schemas/mydata/defaultexperiment",
                    "resource_uri": "/api/v1/schema/31/",
                    "subtype": "",
                    "type": 1
                }
            }
        ],
        "resource_uri": "/api/v1/mydata_experiment/2551/",
        "title": postData['title'],
    }
    mytardis.wfile.write(json.dumps(experimentJson).encode())


def RespondToObjectAclRequest(mytardis, apiUsername):
    """
    Respond to an ObjectACL-related request.

    :param mytardis: The FakeMyTardisHandler instance
    :param apiUsername: The authenticated username
    """
    if apiUsername == "userwithoutprofile":
        mytardis.send_response(404)
        mytardis.send_header("Content-type", "text/html")
        mytardis.end_headers()
        return
    mytardis.send_response(201)
    objectaclJson = dict()
    mytardis.wfile.write(json.dumps(objectaclJson).encode())


def RespondToDatasetRequest(mytardis, postData):
    """
    Respond to an dataset-related request.

    :param mytardis: The FakeMyTardisHandler instance
    :param postData: The POST data dict
    """
    description = postData['description']
    if description == "New Dataset Folder Without Permission":
        mytardis.send_response(401)
        mytardis.send_header("Content-type", "text/html")
        mytardis.end_headers()
        mytardis.wfile.write(b"<html><head><title>"
                             b"FakeMyTardisServer API - Unauthorized"
                             b"</title></head>")
        mytardis.wfile.write(b"<body><h2>Unauthorized</h2>")
        mytardis.wfile.write(b"</body></html>")
        return
    if description == "New Dataset Folder With Internal Server Error":
        mytardis.send_response(500)
        mytardis.send_header("Content-type", "text/html")
        mytardis.end_headers()
        errorJson = {
            "error_message": ("Sorry, this request could not be "
                              "processed. Please try again later.")
        }
        mytardis.wfile.write(json.dumps(errorJson).encode())
        return
    mytardis.send_response(201)
    mytardis.send_header("Content-type", "text/html")
    mytardis.end_headers()
    experimentResourceUri = postData['experiments'][0]
    experimentId = experimentResourceUri.split("/")[-2]
    datasetJson = {
        "description": description,
        "directory": "",
        "experiments": [
            "/api/v1/experiment/%s/" % experimentId
        ],
        "id": 4457,
        "immutable": postData['immutable'],
        "instrument": {
            "facility": TEST_FACILITY,
            "id": 31,
            "name": "Test Instrument",
            "resource_uri": "/api/v1/instrument/31/"
        },
        "parameter_sets": [],
        "resource_uri": "/api/v1/dataset/4457/"
    }
    mytardis.wfile.write(json.dumps(datasetJson).encode())


def RespondToInstrumentRequest(mytardis, postData):
    """
    Respond to an instrument-related request.

    :param mytardis: The FakeMyTardisHandler instance
    :param postData: The POST data dict
    """
    mytardis.send_response(201)
    mytardis.send_header("Content-type", "text/html")
    mytardis.end_headers()
    name = postData['name']
    instrumentJson = {
        "id": 32,
        "name": name,
        "facility": TEST_FACILITY,
        "resource_uri": "/api/v1/instrument/32/"
    }
    mytardis.wfile.write(json.dumps(instrumentJson).encode())


def RespondToUploaderRegRequest(mytardis, postData):
    """
    Respond to a request querying an uploader registration request

    :param mytardis: The FakeMyTardisHandler instance
    :param postData: The POST data dict
    """
    mytardis.send_response(201)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    uploaderResourceUri = postData['uploader']
    fingerprint = postData['requester_key_fingerprint']
    uploaderRegistrationRequestJson = {
        "id": 25,
        "approved": False,
        "approved_storage_box": None,
        "requester_key_fingerprint": fingerprint,
        "resource_uri": "/api/v1/mydata_uploaderregistrationrequest/25/",
        "uploader": uploaderResourceUri
    }
    mytardis.wfile.write(json.dumps(uploaderRegistrationRequestJson).encode())

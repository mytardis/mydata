"""
mydata/tests/fake_mytardis_helpers/get.py

Responses to GET requests for our fake MyTardis server
"""
import copy
import datetime
import re
import json

import six
from six.moves import urllib

from . import EMPTY_API_LIST, STAGING_PATH, TEST_FACILITY, TEST_INSTRUMENT
from . import RespondToRequestForStatusCode, RespondWithStatusCode

# This storage box attribute can be overwritten by an ephemeral port:
SCP_PORT = 2200


def FakeMyTardisGet(mytardis):
    """
    Respond to a GET request.

    :param mytardis: The FakeMyTardisHandler instance
    """
    if mytardis.path.startswith("/redirect") or \
            mytardis.path.startswith("/different_url"):
        mytardis.do_HEAD()
        return

    if mytardis.path.startswith("/request/connectionerror/"):
        mytardis.server.server_close()
        return

    if re.match(r"^/request/http/code/(\d+)/.*$", mytardis.path):
        RespondToRequestForStatusCode(mytardis)
        return

    if mytardis.path == "/" or mytardis.path == "/api/v1/?format=json":
        # "/" is for testing opening MyTardis's web interface
        # (as distinct from its RESTful API).
        # "/api/v1/?format=json" is used in settings validation to ensure
        # that the MyTardis server is accessible and that its API responds
        # in a reasonable time.
        RespondWithStatusCode(mytardis, 200)
        return

    if not mytardis.path.startswith("/api/v1/"):
        raise Exception(
            "Fake MyTardis server doesn't know how to respond to %s"
            % mytardis.path)

    authorization = mytardis.headers.get("Authorization", "")
    match = re.match(r"^ApiKey (\S+):(\S+)$", authorization)
    apiKey = match.groups()[1]
    if apiKey == "invalid":
        RespondWithStatusCode(mytardis, 401)
        return

    responderForPrefix = {
        "/api/v1/facility/": RespondToFacilityRequest,
        "/api/v1/instrument/": RespondToInstrumentRequest,
        "/api/v1/user/": RespondToUserRequest,
        "/api/v1/group/": RespondToGroupRequest,
        "/api/v1/mydata_uploader/": RespondToUploaderRequest,
        "/api/v1/mydata_uploaderregistrationrequest/":
            RespondToUploaderRegRequest,
        "/api/v1/mydata_experiment/": RespondToExperimentRequest,
        "/api/v1/dataset/": RespondToDatasetRequest,
        "/api/v1/mydata_replica/": RespondToReplicaRequest
    }

    for prefix, responder in six.iteritems(responderForPrefix):
        if mytardis.path.startswith(prefix):
            responder(mytardis)
            return

    if re.match(r"^.*&dataset__id=(\S+)&filename=(\S+)&directory=(\S*)$",
                mytardis.path):
        RespondToDataFilesRequest(mytardis)
    elif re.match(r"^/api/v1/mydata_dataset_file/(\d+)/\?format=json$",
                  mytardis.path):
        RespondToDataFileRequest(mytardis)
    elif re.match(r"^/api/v1/dataset_file/([0-9]+)/verify/$",
                  mytardis.path):
        RespondToVerifyRequest(mytardis)
    else:
        raise Exception("FakeMyTardis Server doesn't know how to respond "
                        "to GET: %s" % mytardis.path)


def RespondToFacilityRequest(mytardis):
    """
    Respond to a facility-related request.

    For now, the only supported request is to list all facilities
    the authenticated user has access to.

    :param mytardis: The FakeMyTardisHandler instance
    """
    assert mytardis.path == "/api/v1/facility/?format=json"
    mytardis.send_response(200)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    facilitiesJson = copy.deepcopy(EMPTY_API_LIST)
    facilitiesJson['meta']['total_count'] = 1
    facilitiesJson['objects'] = [TEST_FACILITY]
    mytardis.wfile.write(json.dumps(facilitiesJson))


def RespondToInstrumentRequest(mytardis):
    """
    Respond to an instrument-related request.

    :param mytardis: The FakeMyTardisHandler instance
    """
    baseRequestPath = "/api/v1/instrument/?format=json&facility__id=2&name="
    supportedRequests = dict(
        newInstrument="%sNew%%20Instrument" % baseRequestPath,
        renamedInstrument="%sRenamed%%20Instrument" % baseRequestPath,
        testInstrument="%sTest%%20Instrument" % baseRequestPath,
        testInstrument2="%sTest%%20Instrument2" % baseRequestPath,
        instrument1="%sInstrument1" % baseRequestPath)
    assert mytardis.path in supportedRequests.values()
    mytardis.send_response(200)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    if mytardis.path == supportedRequests['newInstrument']:
        mytardis.wfile.write(json.dumps(EMPTY_API_LIST))
    elif mytardis.path == supportedRequests['renamedInstrument']:
        mytardis.wfile.write(json.dumps(EMPTY_API_LIST))
    elif mytardis.path == supportedRequests['testInstrument']:
        instrumentsJson = copy.deepcopy(EMPTY_API_LIST)
        instrumentsJson['meta']['total_count'] = 1
        instrumentsJson['objects'] = [TEST_INSTRUMENT]
        mytardis.wfile.write(json.dumps(instrumentsJson))
    elif mytardis.path == supportedRequests['testInstrument2']:
        instrumentsJson = copy.deepcopy(EMPTY_API_LIST)
        instrumentsJson['meta']['total_count'] = 1
        instrumentsJson['objects'] = [
            {
                "facility": TEST_FACILITY,
                "id": 18,
                "name": "Test Instrument2",
                "resource_uri": "/api/v1/instrument/18/"
            }
        ]
        mytardis.wfile.write(json.dumps(instrumentsJson))
    elif mytardis.path == supportedRequests['instrument1']:
        instrumentsJson = copy.deepcopy(EMPTY_API_LIST)
        instrumentsJson['meta']['total_count'] = 1
        instrumentsJson['objects'] = [
            {
                "id": 1,
                "name": "Instrument1",
                "facility": TEST_FACILITY,
                "resource_uri": "/api/v1/instrument/1/"
            }
        ]
        mytardis.wfile.write(json.dumps(instrumentsJson))


def RespondToUserRequest(mytardis):
    """
    Respond to a user-related request.

    :param mytardis: The FakeMyTardisHandler instance
    """
    supportedRequests = dict(
        testfacilityUsername="%s&username=testfacility",
        testfacilityEmail="%s&email__iexact=testfacility%%40example.com",
        testuser1Username="%s&username=testuser1",
        testuser1Email="%s&email__iexact=testuser1%%40example.com",
        testuser2Username="%s&username=testuser2",
        testuser2Email="%s&email__iexact=testuser2%%40example.com",
        testuser3Username="%s&username=testuser3",
        testuser3Email="%s&email__iexact=testuser3%%40example.com",
        invalidUserUsername="%s&username=INVALID_USER",
        invalidUserEmail="%s&email__iexact=invalid%%40email.com",
        userWithoutProfile="%s&username=userwithoutprofile"
    )
    baseRequestPath = "/api/v1/user/?format=json"
    for key in supportedRequests:
        supportedRequests[key] = supportedRequests[key] % baseRequestPath
    assert mytardis.path in supportedRequests.values()
    mytardis.send_response(200)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    usersJson = copy.deepcopy(EMPTY_API_LIST)
    if mytardis.path not in (supportedRequests['invalidUserUsername'],
                             supportedRequests['invalidUserEmail']):
        usersJson['meta']['total_count'] = 1
    if mytardis.path == supportedRequests['testfacilityUsername'] or \
            mytardis.path == supportedRequests['testfacilityEmail']:
        usersJson['objects'] = [
            {
                "username": "testfacility",
                "email": "testfacility@example.com",
                "first_name": "Test",
                "last_name": "Facility",
                "groups": [
                    {
                        "id": 2,
                        "name": "test_facility_managers",
                        "resource_uri": "/api/v1/group/2/"}
                ],
                "id": 7,
                "resource_uri": "/api/v1/user/7/"
            }
        ]
    elif mytardis.path == supportedRequests['testuser1Username'] or \
            mytardis.path == supportedRequests['testuser1Email']:
        usersJson['objects'] = [
            {
                "username": "testuser1",
                "first_name": "Test",
                "last_name": "User1",
                "email": "testuser1@example.com",
                "groups": [],
                "id": 148,
                "resource_uri": "/api/v1/user/148/"
            }
        ]
    elif mytardis.path == supportedRequests['testuser2Username'] or \
            mytardis.path == supportedRequests['testuser2Email']:
        usersJson['objects'] = [
            {
                "username": "testuser2",
                "first_name": "Test",
                "last_name": "User2",
                "email": "testuser2@example.com",
                "groups": [],
                "id": 149,
                "resource_uri": "/api/v1/user/149/"
            }
        ]
    elif mytardis.path == supportedRequests['testuser3Username'] or \
            mytardis.path == supportedRequests['testuser3Email']:
        usersJson['objects'] = [
            {
                "username": "testuser3",
                "first_name": "Test",
                "last_name": "User3",
                "email": "testuser3@example.com",
                "groups": [],
                "id": 150,
                "resource_uri": "/api/v1/user/150/"
            }
        ]
    elif mytardis.path == supportedRequests['invalidUserUsername'] or \
            mytardis.path == supportedRequests['invalidUserEmail']:
        pass  # Return the default usersJson, i.e. EMPTY_API_LIST
    elif mytardis.path == supportedRequests['userWithoutProfile']:
        usersJson['objects'] = [
            {
                "username": "userwithoutprofile",
                "first_name": "User",
                "last_name": "Without Profile",
                "email": "userwithoutprofile@example.com",
                "groups": [],
                "id": 1148,
                "resource_uri": "/api/v1/user/1148/"
            }
        ]
    mytardis.wfile.write(json.dumps(usersJson))


def RespondToGroupRequest(mytardis):
    """
    Respond to a group-related request.

    :param mytardis: The FakeMyTardisHandler instance
    """
    baseRequestPath = "/api/v1/group/?format=json"
    supportedRequests = dict(
        group1="%s&name=TestFacility-Group1" % baseRequestPath,
        group2="%s&name=TestFacility-Group2" % baseRequestPath,
        invalidGroupName="%s&name=INVALID_GROUP" % baseRequestPath,
    )
    assert mytardis.path in supportedRequests.values()
    mytardis.send_response(200)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    groupsJson = copy.deepcopy(EMPTY_API_LIST)
    if mytardis.path != supportedRequests['invalidGroupName']:
        groupsJson['meta']['total_count'] = 1
    if mytardis.path == supportedRequests['group1']:
        groupsJson['meta']['total_count'] = 1
        groupsJson['objects'] = [
            {
                "id": "101",
                "name": "TestFacility-Group1",
                "resource_uri": "/api/v1/group/1/"
            }
        ]
    elif mytardis.path == supportedRequests['group2']:
        groupsJson['meta']['total_count'] = 1
        groupsJson['objects'] = [
            {
                "id": "102",
                "name": "TestFacility-Group2",
                "resource_uri": "/api/v1/user/2/"
            }
        ]
    elif mytardis.path == supportedRequests['invalidGroupName']:
        pass  # Return the default groupsJson, i.e. EMPTY_API_LIST
    mytardis.wfile.write(json.dumps(groupsJson))


def RespondToUploaderRequest(mytardis):
    """
    Respond to an uploader-related request.

    :param mytardis: The FakeMyTardisHandler instance
    """
    match = re.match(r"^.*uuid=(\S+)$", mytardis.path)
    uuid = urllib.parse.unquote(match.groups()[0])
    mytardis.send_response(200)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    uploadersJson = copy.deepcopy(EMPTY_API_LIST)
    uploadersJson['meta']['total_count'] = 1
    uploadersJson['objects'] = [
        {
            "id": 1,
            "name": "Test Instrument",
            "uuid": uuid,
            "instruments": [TEST_INSTRUMENT],
            "resource_uri": "/api/v1/mydata_uploader/25/",
            "settings_updated": datetime.datetime.now().isoformat(),
            "settings": [
                {"key": "contact_name", "value": "Someone Else"},
                {"key": "validate_folder_structure", "value": "False"},
                {"key": "max_verification_threads", "value": "2"},
                {"key": "scheduled_date", "value": "2020-01-01"},
                {"key": "scheduled_time", "value": "09:00:00"}
            ]
        }
    ]
    mytardis.wfile.write(json.dumps(uploadersJson))


def RespondToUploaderRegRequest(mytardis):
    """
    Respond to a request querying an uploader registration request.

    :param mytardis: The FakeMyTardisHandler instance
    """
    match = re.match(r"^.*uploader__uuid=(\S+)"
                     r"&requester_key_fingerprint=(\S+)$", mytardis.path)
    if match:
        uuid = urllib.parse.unquote(match.groups()[0])
        existingApprovedRequest = (uuid == "1234567890")
        missingStorageBoxAttribute = (uuid == "1234567891")
        fingerprint = urllib.parse.unquote(match.groups()[1])
    else:
        mytardis.send_response(400)
        mytardis.send_header("Content-type", "application/json")
        mytardis.end_headers()
        errorJson = {"error_message":
                     "Missing RSA key fingerprint in GET query"}
        mytardis.wfile.write(json.dumps(errorJson))
        return
    mytardis.send_response(200)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    if existingApprovedRequest or missingStorageBoxAttribute:
        uploaderRegRequestsJson = copy.deepcopy(EMPTY_API_LIST)
        uploaderRegRequestsJson['meta']['total_count'] = 1
        uploaderRegRequestsJson['objects'] = [
            {
                "id": 25,
                "name": "Fake UploaderName",
                "approved": True,
                "approved_storage_box": {
                    "id": 10,
                    "name": "test-staging",
                    "description": "Test Staging",
                    "django_storage_class":
                        "tardis.tardis_portal.storage"
                        ".MyTardisLocalFileSystemStorage",
                    "max_size": "10566819840",
                    "status": "dirty",
                    "attributes": [
                        {
                            "id": 10,
                            "key": "scp_username",
                            "resource_uri": "/api/v1/storageboxattribute/10/",
                            "storage_box": "/api/v1/storagebox/10/",
                            "value": "mydata"
                        },
                        {
                            "id": 11,
                            "key": "scp_hostname",
                            "resource_uri": "/api/v1/storageboxattribute/11/",
                            "storage_box": "/api/v1/storagebox/10/",
                            "value": "localhost",
                        },
                        {
                            "id": 12,
                            "key": "type",
                            "resource_uri": "/api/v1/storageboxattribute/12/",
                            "storage_box": "/api/v1/storagebox/10/",
                            "value": "receiving"
                        },
                        {
                            "id": 13,
                            "key": "scp_port",
                            "resource_uri": "/api/v1/storageboxattribute/13/",
                            "storage_box": "/api/v1/storagebox/10/",
                            "value": str(SCP_PORT),
                        },
                    ],
                    "options": [
                        {
                            "id": 8,
                            "key": "location",
                            "resource_uri": "/api/v1/storageboxoption/8/",
                            "storage_box": "/api/v1/storagebox/10/",
                            "value": STAGING_PATH
                        }
                    ],
                    "resource_uri": "/api/v1/storagebox/10/",
                },
                "requester_key_fingerprint": fingerprint,
                "resource_uri":
                    "/api/v1/mydata_uploaderregistrationrequest/25/",
                "uploader": "/api/v1/mydata_uploader/25/"
            }
        ]
        if missingStorageBoxAttribute:
            uploaderRegRequest = uploaderRegRequestsJson['objects'][0]
            attrs = \
                uploaderRegRequest['approved_storage_box']['attributes']
            attrNum = -1
            for attr in attrs:
                if attr['key'] == 'scp_username':
                    attrNum = attrs.index(attr)
                    break
            if attrNum != -1:
                attrs.pop(attrNum)
    else:
        uploaderRegRequestsJson = EMPTY_API_LIST
    mytardis.wfile.write(json.dumps(uploaderRegRequestsJson))


def RespondToExperimentRequest(mytardis):
    """
    Respond to an experiment-related request.

    :param mytardis: The FakeMyTardisHandler instance
    """
    baseRequestPath = "/api/v1/mydata_experiment/?format=json"
    supportedRequestPrefixes = dict(
        title="%s&title=" % baseRequestPath,
        uploader="%s&uploader=" % baseRequestPath)
    assert mytardis.path.startswith(supportedRequestPrefixes['title']) or \
        mytardis.path.startswith(supportedRequestPrefixes['uploader'])
    experimentsJson = copy.deepcopy(EMPTY_API_LIST)
    experimentsJson['meta']['total_count'] = 1
    if mytardis.path.startswith(supportedRequestPrefixes['title']):
        match = re.match(r"^.*&title=(\S+)&folder_structure.*$", mytardis.path)
        title = urllib.parse.unquote(match.groups()[0])
        if title == "Missing UserProfile":
            RespondWithStatusCode(
                mytardis, 404, "UserProfile matching query does not exist.")
            return
        if title == "Missing Schema":
            RespondWithStatusCode(
                mytardis, 404, "Schema matching query does not exist.")
            return
        if title == "Unknown 404":
            RespondWithStatusCode(mytardis, 404)
            return
        mytardis.send_response(200)
        mytardis.send_header("Content-type", "application/json")
        experimentsJson = copy.deepcopy(EMPTY_API_LIST)
        mytardis.end_headers()
        if title == "Existing Experiment":
            experimentsJson['meta']['total_count'] = 1
            experimentsJson['objects'] = [
                {
                    "description": "",
                    "id": 2552,
                    "institution_name": "Monash University",
                    "resource_uri": "/api/v1/mydata_experiment/2552/",
                    "title": "Existing Experiment",
                }
            ]
        elif title == "Multiple Existing Experiments":
            experimentsJson['meta']['total_count'] = 2
            experimentsJson['objects'] = [
                {
                    "description": "",
                    "id": 2552,
                    "institution_name": "Monash University",
                    "resource_uri": "/api/v1/mydata_experiment/2552/",
                    "title": "Existing Experiment1",
                },
                {
                    "description": "",
                    "id": 2553,
                    "institution_name": "Monash University",
                    "resource_uri": "/api/v1/mydata_experiment/2553/",
                    "title": "Existing Experiment2",
                }
            ]
        mytardis.wfile.write(json.dumps(experimentsJson))
    elif mytardis.path.startswith(supportedRequestPrefixes['uploader']):
        match = re.match(r"^.*&uploader=(\S+)&user_folder_name.*$",
                         mytardis.path)
        if not match:
            match = re.match(r"^.*&uploader=(\S+)&group_folder_name.*$",
                             mytardis.path)
        if not match:
            match = re.match(r"^.*&uploader=(\S+)$", mytardis.path)

        uploaderUuid = urllib.parse.unquote(match.groups()[0])
        mytardis.send_response(200)
        mytardis.send_header("Content-type", "application/json")
        mytardis.end_headers()
        experimentsJson = copy.deepcopy(EMPTY_API_LIST)
        if uploaderUuid == "Existing Experiment":
            experimentsJson['meta']['total_count'] = 1
            experimentsJson['objects'] = [
                {
                    "description": "",
                    "id": 2552,
                    "resource_uri": "/api/v1/mydata_experiment/2552/",
                    "title": "Existing Experiment",
                }
            ]
        elif uploaderUuid == "Multiple Existing Experiments":
            experimentsJson['meta']['total_count'] = 2
            experimentsJson['objects'] = [
                {
                    "description": "",
                    "id": 2552,
                    "resource_uri": "/api/v1/mydata_experiment/2552/",
                    "title": "Existing Experiment1",
                },
                {
                    "description": "",
                    "id": 2553,
                    "resource_uri": "/api/v1/mydata_experiment/2553/",
                    "title": "Existing Experiment2",
                }
            ]
        mytardis.wfile.write(json.dumps(experimentsJson))


def RespondToDatasetRequest(mytardis):
    """
    Respond to a dataset-related request.

    :param mytardis: The FakeMyTardisHandler instance
    """
    match = re.match(
        r"^.*&experiments__id=(\S+)&description=(\S+)&instrument__id=(\S+)$",
        mytardis.path)
    description = urllib.parse.unquote(match.groups()[1])
    instrumentId = urllib.parse.unquote(match.groups()[2])
    mytardis.send_response(200)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    datasetsJson = copy.deepcopy(EMPTY_API_LIST)
    if description == "Existing Dataset":
        datasetsJson['meta']['total_count'] = 1
        datasetsJson['objects'] = [
            {
                "id": "1001",
                "description": description,
                "instrument": "/api/v1/instrument/%s/" % instrumentId,
                "experiments": ["/api/v1/experiment/2552/"]
            }
        ]
    mytardis.wfile.write(json.dumps(datasetsJson))


def RespondToDataFilesRequest(mytardis):
    """
    Respond to a datafile-related request, which performs a query which could
    return more than one DataFile, i.e.  the request should use the
    /api/v1/mydata_dataset_file/ endpoint possibly with filter parameters,
    rather than the /api/v1/mydata_dataset_file/[datafile_id]/ endpoint which
    will only return one DataFile.

    :param mytardis: The FakeMyTardisHandler instance
    """
    match = re.match(
        r"^.*&dataset__id=(\S+)&filename=(\S+)&directory=(\S*)$",
        mytardis.path)
    datasetId = match.groups()[0]
    filename = urllib.parse.unquote(match.groups()[1])
    directory = urllib.parse.unquote(match.groups()[2])
    mytardis.send_response(200)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    datafilesJson = copy.deepcopy(EMPTY_API_LIST)
    if filename == "existing_unverified_incomplete_file.txt":
        datafilesJson['meta']['total_count'] = 1
        datafilesJson['objects'] = [
            {
                "id": 290385,
                "created_time": "2015-06-25T00:26:21",
                "datafile": None,
                "dataset": "/api/v1/dataset/%s/" % datasetId,
                "deleted": False,
                "deleted_time": None,
                "directory": directory,
                "filename": filename,
                "md5sum": "c033080e8b2ec59e37fb1a9dc341c813",
                "mimetype": "image/jpeg",
                "modification_time": None,
                "parameter_sets": [],
                "replicas": [
                    {
                        "created_time": "2015-10-06T10:21:48.910470",
                        "datafile": "/api/v1/dataset_file/290385/",
                        "id": 444891,
                        "last_verified_time": "2015-10-06T10:21:53.952521",
                        "resource_uri": "/api/v1/replica/444891/",
                        "uri": "DatasetDescription-%s/%s" % (datasetId,
                                                             filename),
                        "verified": False
                    }
                ],
                "resource_uri": "/api/v1/mydata_dataset_file/290385/",
                "sha512sum": "",
                "size": "36",
                "version": 1
            }
        ]
    elif filename == "existing_unverified_full_size_file.txt":
        datafilesJson['meta']['total_count'] = 1
        datafilesJson['objects'] = [
            {
                "id": 290385,
                "created_time": "2015-06-25T00:26:21",
                "datafile": None,
                "dataset": "/api/v1/dataset/%s/" % datasetId,
                "deleted": False,
                "deleted_time": None,
                "directory": directory,
                "filename": filename,
                "md5sum": "e71c538337dce5b7fd36ae8db8160756",
                "mimetype": "image/jpeg",
                "modification_time": None,
                "parameter_sets": [],
                "replicas": [
                    {
                        "created_time": "2015-10-06T10:21:48.910470",
                        "datafile": "/api/v1/dataset_file/290385/",
                        "id": 444892,
                        "last_verified_time": "2015-10-06T10:21:53.952521",
                        "resource_uri": "/api/v1/replica/444892/",
                        "uri": "DatasetDescription-%s/%s" % (datasetId,
                                                             filename),
                        "verified": False
                    }
                ],
                "resource_uri": "/api/v1/mydata_dataset_file/290385/",
                "sha512sum": "",
                "size": "35",
                "version": 1
            }
        ]
    elif filename == "existing_verified_file.txt":
        datafilesJson['meta']['total_count'] = 1
        datafilesJson['objects'] = [
            {
                "id": 290386,
                "created_time": "2015-06-25T00:26:21",
                "datafile": None,
                "dataset": "/api/v1/dataset/%s/" % datasetId,
                "deleted": False,
                "deleted_time": None,
                "directory": directory,
                "filename": filename,
                "md5sum": "0d2a8fb0a57bf4a9aabce5f7e69b36e9",
                "mimetype": "image/jpeg",
                "modification_time": None,
                "parameter_sets": [],
                "replicas": [
                    {
                        "created_time": "2015-10-06T10:21:48.910470",
                        "datafile": "/api/v1/dataset_file/290386/",
                        "id": 444893,
                        "last_verified_time": "2015-10-06T10:21:53.952521",
                        "resource_uri": "/api/v1/replica/444893/",
                        "uri": "DatasetDescription-%s/%s" % (datasetId,
                                                             filename),
                        "verified": True
                    }
                ],
                "resource_uri": "/api/v1/mydata_dataset_file/290386/",
                "sha512sum": "",
                "size": "23",
                "version": 1
            }
        ]
    elif filename == "missing_mydata_replica_api_endpoint.txt":
        datafilesJson['meta']['total_count'] = 1
        datafilesJson['objects'] = [
            {
                "id": 290387,
                "created_time": "2015-06-25T00:26:21",
                "datafile": None,
                "dataset": "/api/v1/dataset/%s/" % datasetId,
                "deleted": False,
                "deleted_time": None,
                "directory": directory,
                "filename": filename,
                "md5sum": "0d2a8fb0a57bf4a9aabce5f7e69b36e9",
                "mimetype": "image/jpeg",
                "modification_time": None,
                "parameter_sets": [],
                "replicas": [
                    {
                        "created_time": "2015-10-06T10:21:48.910470",
                        "datafile": "/api/v1/dataset_file/290387/",
                        "id": 444894,
                        "last_verified_time": "2015-10-06T10:21:53.952521",
                        "resource_uri": "/api/v1/replica/444894/",
                        "uri": "DatasetDescription-%s/%s" % (datasetId,
                                                             filename),
                        "verified": True
                    }
                ],
                "resource_uri": "/api/v1/mydata_dataset_file/290387/",
                "sha512sum": "",
                "size": "23",
                "version": 1
            }
        ]
    mytardis.wfile.write(json.dumps(datafilesJson))


def RespondToDataFileRequest(mytardis):
    """
    Respond to a datafile-related request, which performs a query which will
    only return one DataFile (or raise an error), i.e. the request should use
    the /api/v1/mydata_dataset_file/[datafile_id]/ endpoint, rather than the
    /api/v1/mydata_dataset_file/ endpoint.

    :param mytardis: The FakeMyTardisHandler instance
    """
    match = re.match(r"^/api/v1/mydata_dataset_file/(\d+)/\?format=json$",
                     mytardis.path)
    if match:
        dataFileId = match.groups()[0]
        replicaId = dataFileId
    else:
        mytardis.send_response(400)
        mytardis.send_header("Content-type", "application/json")
        mytardis.end_headers()
        errorJson = {
            "error_message":
            "Missing DataFile ID "
            "in mydata_dataset_file GET query"
        }
        mytardis.wfile.write(json.dumps(errorJson))
        return
    mytardis.send_response(200)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    datafileJson = {
        "id": dataFileId,
        "replicas": [
            {
                "id": replicaId,
                "datafile": "/api/v1/dataset_file/%s/" % dataFileId
            }
        ],
    }
    mytardis.wfile.write(json.dumps(datafileJson))


def RespondToReplicaRequest(mytardis):
    """
    Respond to a DFO-related request.

    The API endpoint for DataFileObjects (DFOs) is:
    /api/v1/replica/ or
    /api/v1/mydata_replica/ for the version in the mytardis-app-mydata app,
    because MyTardis's DataFileObject model replaced a similar model called
    "Replica".

    :param mytardis: The FakeMyTardisHandler instance
    """
    match = re.match(r"^/api/v1/mydata_replica/(\d+)/\?format=json$",
                     mytardis.path)
    if match:
        replicaId = match.groups()[0]
    else:
        mytardis.send_response(400)
        mytardis.send_header("Content-type", "application/json")
        mytardis.end_headers()
        errorJson = {
            "error_message":
            "Missing DFO ID "
            "in mydata_replica GET query"
        }
        mytardis.wfile.write(json.dumps(errorJson))
        return
    if replicaId == "444894":  # missing_mydata_replica_api_endpoint.txt
        mytardis.send_response(404)
        return
    mytardis.send_response(200)
    mytardis.send_header("Content-type", "application/json")
    mytardis.end_headers()
    if replicaId == "444891":  # existing_incomplete_file.txt
        replicaJson = {
            "id": replicaId,
            "size": 30  # 30 out of 36 bytes uploaded.
        }
    elif replicaId == "444892":  # existing_full_size_file.txt
        replicaJson = {
            "id": replicaId,
            "size": 35  # 35 out of 35 bytes uploaded.
        }
    else:
        replicaJson = {
            "id": replicaId,
            "size": 1024
        }
    mytardis.wfile.write(json.dumps(replicaJson))


def RespondToVerifyRequest(mytardis):
    """
    Respond to a request to verify a DataFile.

    Just return 200 (OK) for now.

    :param mytardis: The FakeMyTardisHandler instance
    """
    mytardis.send_response(200)
    mytardis.end_headers()

"""
fake_mytardis_server.py

A simple HTTP server to use for unit testing in MyData.

Many of the responses given by this fake MyTardis server
have been copied and pasted from a real MyTardis server's
responses and hard-coded below.  In some cases, unnecessary
fields have been removed from the JSON responses.
"""
# pylint: disable=too-many-lines
import datetime
import sys
import BaseHTTPServer
import re
import json
import tempfile
import os
import urllib
import cgi
import logging

from mydata.utils.openssh import GetCygwinPath

DEBUG = False

logger = logging.getLogger(__name__)

handle = tempfile.NamedTemporaryFile()  # pylint: disable=invalid-name
handle.close()
STAGING_PATH = handle.name
os.makedirs(STAGING_PATH)
logger.info("Created temporary staging directory: %s",
            STAGING_PATH)
if sys.platform.startswith("win"):
    STAGING_PATH = GetCygwinPath(STAGING_PATH)


class FakeMyTardisHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    This class is used to handle the HTTP requests that arrive at the server.

    The handler will parse the request and the headers, then call a method
    specific to the request type. The method name is constructed from the
    request. For example, for the request method SPAM, the do_SPAM() method
    will be called with no arguments. All of the relevant information is
    stored in instance variables of the handler. Subclasses should not need
    to override or extend the __init__() method.
    """
    datafileIdAutoIncrement = 0

    def do_HEAD(self):  # pylint: disable=invalid-name
        """
        Respond to a HEAD request
        """
        if self.path.startswith("/redirect"):
            self.send_response(302)
            self.send_header("Location",
                             self.path.replace('redirect', 'different_url'))
        else:
            self.send_response(200)
        self.end_headers()

    def do_GET(self):  # pylint: disable=invalid-name
        """
        Respond to a GET request.
        """
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-return-statements
        if self.path.startswith("/redirect") or \
                self.path.startswith("/different_url"):
            self.do_HEAD()
            return

        if self.path.startswith("/request/http/code/"):
            match = re.match(r"^/request/http/code/(\d+)/.*$", self.path)
            if match:
                httpCode = int(match.groups()[0])
            else:
                httpCode = 500
            self.send_response(httpCode)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            fakeJson = "{}"
            self.wfile.write(json.dumps(fakeJson))
            return

        if self.path.startswith("/api/v1/"):
            if self.path == "/api/v1/?format=json":
                # We use this path to test that the MyTardis servers is
                # accessible and that the API responds in a reasonable time.
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                fakeJson = "{}"
                self.wfile.write(json.dumps(fakeJson))
                return
            authorized = False
            authorization = self.headers.getheader("Authorization", "")
            match = re.match(r"^ApiKey (\S+):(\S+)$", authorization)
            if match:
                _ = urllib.unquote(match.groups()[0])  # username
                apiKey = urllib.unquote(match.groups()[1])  # API key
                if apiKey != "invalid":
                    authorized = True
            if not authorized:
                self.send_response(401)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("<html><head><title>"
                                 "FakeMyTardisServer API - Unauthorized"
                                 "</title></head>")
                self.wfile.write("<body><h2>Unauthorized</h2>")
                self.wfile.write("</body></html>")
                return

        if self.path == "/api/v1/facility/?format=json":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            facilitiesJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
                    {
                        "id": 2,
                        "manager_group":
                        {
                            "id": 2,
                            "name": "test_facility_managers",
                            "resource_uri": "/api/v1/group/2/"
                        },
                        "name": "Test Facility",
                        "resource_uri": "/api/v1/facility/2/"
                    }
                ]
            }
            self.wfile.write(json.dumps(facilitiesJson))
        elif self.path == \
                "/api/v1/instrument/?format=json&facility__id=2&name=New%20Instrument":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            instrumentsJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 0
                },
                "objects": []
            }
            self.wfile.write(json.dumps(instrumentsJson))
        elif self.path == \
                "/api/v1/instrument/?format=json&facility__id=2&name=Renamed%20Instrument":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            instrumentsJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 0
                },
                "objects": []
            }
            self.wfile.write(json.dumps(instrumentsJson))
        elif self.path == \
                "/api/v1/instrument/?format=json&facility__id=2&name=Test%20Instrument":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            instrumentsJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
                    {
                        "facility": {
                            "id": 2,
                            "manager_group": {
                                "id": 2,
                                "name": "test_facility_managers",
                                "resource_uri": "/api/v1/group/2/"
                            },
                            "name": "Test Facility",
                            "resource_uri": "/api/v1/facility/2/"
                        },
                        "id": 17,
                        "name": "Test Instrument",
                        "resource_uri": "/api/v1/instrument/17/"
                    }
                ]
            }
            self.wfile.write(json.dumps(instrumentsJson))
        elif self.path == \
                "/api/v1/instrument/?format=json&facility__id=2&name=Test%20Instrument2":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            instrumentsJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
                    {
                        "facility": {
                            "id": 2,
                            "manager_group": {
                                "id": 2,
                                "name": "test_facility_managers",
                                "resource_uri": "/api/v1/group/2/"
                            },
                            "name": "Test Facility",
                            "resource_uri": "/api/v1/facility/2/"
                        },
                        "id": 18,
                        "name": "Test Instrument2",
                        "resource_uri": "/api/v1/instrument/18/"
                    }
                ]
            }
            self.wfile.write(json.dumps(instrumentsJson))
        elif self.path == "/api/v1/user/?format=json&username=testfacility":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            usersJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
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
            }
            self.wfile.write(json.dumps(usersJson))
        elif self.path == "/api/v1/user/?format=json&username=testuser1" or \
                self.path == ("/api/v1/user/?format=json"
                              "&email__iexact=testuser1%40example.com"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            usersJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
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
            }
            self.wfile.write(json.dumps(usersJson))
        elif self.path == "/api/v1/user/?format=json&username=testuser2" or \
                self.path == ("/api/v1/user/?format=json"
                              "&email__iexact=testuser2%40example.com"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            usersJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
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
            }
            self.wfile.write(json.dumps(usersJson))
        elif self.path == "/api/v1/user/?format=json&username=INVALID_USER":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            usersJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 0
                },
                "objects": [
                ]
            }
            self.wfile.write(json.dumps(usersJson))
        elif self.path == "/api/v1/group/?format=json&name=TestFacility-Group1":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            groupsJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
                    {
                        "id": "101",
                        "name": "TestFacility-Group1",
                        "resource_uri": "/api/v1/group/1/"
                    }
                ]
            }
            self.wfile.write(json.dumps(groupsJson))
        elif self.path == "/api/v1/group/?format=json&name=TestFacility-Group2":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            groupsJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
                    {
                        "id": "102",
                        "name": "TestFacility-Group2",
                        "resource_uri": "/api/v1/user/2/"
                    }
                ]
            }
            self.wfile.write(json.dumps(groupsJson))
        elif self.path.startswith("/api/v1/instrument/?format=json"
                                  "&facility__id=2&name=Instrument1"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            instrumentsJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
                    {
                        "id": 1,
                        "name": "Instrument1",
                        "facility": {
                            "id": 2,
                            "manager_group": {
                                "id": 2,
                                "name": "test_facility_managers",
                                "resource_uri": "/api/v1/group/2/"
                            },
                            "name": "Test Facility",
                            "resource_uri": "/api/v1/facility/2/"
                        },
                        "resource_uri": "/api/v1/instrument/1/"
                    }
                ]
            }
            self.wfile.write(json.dumps(instrumentsJson))
        elif self.path.startswith("/api/v1/mydata_uploader/?format=json&uuid="):
            match = re.match(r"^.*uuid=(\S+)$", self.path)
            if match:
                uuid = urllib.unquote(match.groups()[0])
            else:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {"error_message": "Missing UUID in GET query"}
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            uploadersJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
                    {
                        "id": 1,
                        "name": "Test Instrument",
                        "uuid": uuid,
                        "instruments": [
                            {
                                "id": 31,
                                "name": "Test Instrument",
                                "facility": {
                                    "id": 2,
                                    "manager_group": {
                                        "id": 2,
                                        "name": "test_facility_managers",
                                        "resource_uri": "/api/v1/group/2/"
                                    },
                                    "name": "Test Facility",
                                    "resource_uri": "/api/v1/facility/2/"
                                },
                                "resource_uri": "/api/v1/instrument/31/"
                            }
                        ],
                        "resource_uri": "/api/v1/mydata_uploader/25/",
                        "settings_updated": datetime.datetime.now().isoformat(),
                        "settings": [
                            {
                                "key": "contact_name",
                                "value": "Someone Else"
                            },
                            {
                                "key": "validate_folder_structure",
                                "value": False
                            },
                            {
                                "key": "max_verification_threads",
                                "value": 2
                            },
                            {
                                "key": "scheduled_date",
                                "value": "2020-01-01"
                            },
                            {
                                "key": "scheduled_time",
                                "value": "09:00:00"
                            }
                        ]
                    }
                ]
            }
            self.wfile.write(json.dumps(uploadersJson))
        elif self.path.startswith("/api/v1/mydata_uploaderregistrationrequest"
                                  "/?format=json&uploader__uuid="):
            match = re.match(r"^.*uploader__uuid=(\S+)"
                             r"&requester_key_fingerprint=(\S+)$", self.path)
            if match:
                uuid = urllib.unquote(match.groups()[0])
                approved = (uuid == "1234567890")
                fingerprint = urllib.unquote(match.groups()[1])
            else:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {"error_message":
                             "Missing RSA key fingerprint in GET query"}
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            uploadersJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
                    {
                        "id": 25,
                        "approved": approved,
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
                                    "value": "2200",
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
                        "resource_uri": "/api/v1/mydata_uploaderregistrationrequest/25/",
                        "uploader": "/api/v1/mydata_uploader/25/"
                    }
                ]
            }
            self.wfile.write(json.dumps(uploadersJson))
        elif self.path.startswith("/api/v1/mydata_experiment/?format=json&title="):
            # e.g. /api/v1/mydata_experiment/?format=json
            #      &title=Test%20Instrument%20-%20Test%20User1
            #      &folder_structure=Username%20/%20Dataset
            #      &user_folder_name=testuser1
            match = re.match(r"^.*&title=(\S+)&folder_structure=(\S+)"
                             r"&user_folder_name=(\S+)$", self.path)
            if match:
                title = urllib.unquote(match.groups()[0])  # title
                _ = urllib.unquote(match.groups()[1])  # folder_structure
                _ = urllib.unquote(match.groups()[2])  # user_folder_name
            else:
                match = re.match(r"^.*&title=(\S+)&folder_structure=(\S+)"
                                 r"&group_folder_name=(\S+)$", self.path)
                if match:
                    title = urllib.unquote(match.groups()[0])  # title
                    _ = urllib.unquote(match.groups()[1])  # folder_structure
                    _ = urllib.unquote(match.groups()[2])  # group_folder_name
                else:
                    match = re.match(r"^.*&title=(\S+)&folder_structure=(\S+)$",
                                     self.path)
                    title = urllib.unquote(match.groups()[0])  # title
                    _ = urllib.unquote(match.groups()[1])  # folder_structure
            if not match:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {
                    "error_message":
                    "Missing title, folder_structure or "
                    "user_folder_name / group_folder_name in experiment GET query"
                }
                self.wfile.write(json.dumps(errorJson))
                return
            if title == "Missing UserProfile":
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {
                    "error_message": "UserProfile matching query does not exist."
                }
                self.wfile.write(json.dumps(errorJson))
                return
            elif title == "Missing Schema":
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {
                    "error_message": "Schema matching query does not exist."
                }
                self.wfile.write(json.dumps(errorJson))
                return
            elif title == "Unknown 404":
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {}
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            if title == "Existing Experiment":
                experimentsJson = {
                    "meta": {
                        "limit": 20,
                        "next": None,
                        "offset": 0,
                        "previous": None,
                        "total_count": 1
                    },
                    "objects": [
                        {
                            "description": "",
                            "id": 2552,
                            "institution_name": "Monash University",
                            "resource_uri": "/api/v1/mydata_experiment/2552/",
                            "title": "Existing Experiment",
                        }
                    ]
                }
            elif title == "Multiple Existing Experiments":
                experimentsJson = {
                    "meta": {
                        "limit": 20,
                        "next": None,
                        "offset": 0,
                        "previous": None,
                        "total_count": 2
                    },
                    "objects": [
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
                }
            else:
                experimentsJson = {
                    "meta": {
                        "limit": 20,
                        "next": None,
                        "offset": 0,
                        "previous": None,
                        "total_count": 0
                    },
                    "objects": [
                    ]
                }
            self.wfile.write(json.dumps(experimentsJson))
        elif self.path.startswith("/api/v1/mydata_experiment/?format=json&uploader="):
            # e.g. /api/v1/mydata_experiment/?format=json
            #      &uploader=dacd08a6-e5d3-11e6-8623-a45e60d72633
            #      &user_folder_name=testfacility
            match = re.match(r"^.*&uploader=(\S+)"
                             r"&user_folder_name=(\S+)$", self.path)
            if match:
                uploaderUuid = urllib.unquote(match.groups()[0])  # uploader uuid
                _ = urllib.unquote(match.groups()[1])  # user_folder_name
            else:
                match = re.match(r"^.*&uploader=(\S+)"
                                 r"&group_folder_name=(\S+)$", self.path)
                if match:
                    uploaderUuid = urllib.unquote(match.groups()[0])  # uploader uuid
                    _ = urllib.unquote(match.groups()[1])  # group_folder_name
                else:
                    match = re.match(r"^.*&uploader=(\S+)$", self.path)
                    if match:
                        uploaderUuid = urllib.unquote(match.groups()[0])  # uploader uuid
            if not match:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {
                    "error_message":
                    "Missing title, folder_structure or "
                    "user_folder_name / group_folder_name in experiment GET query"
                }
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            if uploaderUuid == "Existing Experiment":
                experimentsJson = {
                    "meta": {
                        "limit": 20,
                        "next": None,
                        "offset": 0,
                        "previous": None,
                        "total_count": 1
                    },
                    "objects": [
                        {
                            "description": "",
                            "id": 2552,
                            "resource_uri": "/api/v1/mydata_experiment/2552/",
                            "title": "Existing Experiment",
                        }
                    ]
                }
            elif uploaderUuid == "Multiple Existing Experiments":
                experimentsJson = {
                    "meta": {
                        "limit": 20,
                        "next": None,
                        "offset": 0,
                        "previous": None,
                        "total_count": 2
                    },
                    "objects": [
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
                }
            else:
                experimentsJson = {
                    "meta": {
                        "limit": 20,
                        "next": None,
                        "offset": 0,
                        "previous": None,
                        "total_count": 0
                    },
                    "objects": [
                    ]
                }
            self.wfile.write(json.dumps(experimentsJson))
        elif self.path.startswith("/api/v1/dataset/?format=json&experiments__id="):
            # e.g. /api/v1/dataset/?format=json&experiments__id=2551&description=Flowers
            match = re.match(r"^.*&experiments__id=(\S+)&description=(\S+)$", self.path)
            if not match:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {
                    "error_message":
                    "Missing experiment ID or description in dataset GET query"
                }
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            datasetsJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 0
                },
                "objects": [
                ]
            }
            self.wfile.write(json.dumps(datasetsJson))
        elif self.path.startswith("/api/v1/mydata_dataset_file/?format=json&dataset__id="):
            # e.g. /api/v1/mydata_dataset_file/?format=json
            #      &dataset__id=4458
            #      &filename=1024px-Australian_Birds_%40_Jurong_Bird_Park_%284374195521%29.jpg
            #      &directory=
            match = re.match(r"^.*&dataset__id=(\S+)&filename=(\S+)&directory=(\S*)$", self.path)
            if match:
                datasetId = match.groups()[0]
                filename = urllib.unquote(match.groups()[1])
                directory = urllib.unquote(match.groups()[2])
            else:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {
                    "error_message":
                    "Missing dataset ID or filename or directory "
                    "in mydata_dataset_file GET query"
                }
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            testResumingUploads = False
            if testResumingUploads:
                datafilesJson = {
                    "meta": {
                        "limit": 20,
                        "next": None,
                        "offset": 0,
                        "previous": None,
                        "total_count": 1
                    },
                    "objects": [
                        {
                            "id": 290385,
                            "created_time": "2015-06-25T00:26:21",
                            "datafile": None,
                            "dataset": "/api/v1/dataset/%s/" % datasetId,
                            "deleted": False,
                            "deleted_time": None,
                            "directory": directory,
                            "filename": filename,
                            "md5sum": "53c6ac03b64f61d5e0b596f70ed75a51",
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
                                    "uri": "DatasetDescription-%s/%s" % (datasetId, filename),
                                    "verified": False
                                }
                            ],
                            "resource_uri": "/api/v1/mydata_dataset_file/290385/",
                            "sha512sum": "",
                            "size": "116537",
                            "version": 1
                        }
                    ]
                }
            else:
                datafilesJson = {
                    "meta": {
                        "limit": 20,
                        "next": None,
                        "offset": 0,
                        "previous": None,
                        "total_count": 0
                    },
                    "objects": []
                }
            self.wfile.write(json.dumps(datafilesJson))
        elif self.path.startswith("/api/v1/mydata_dataset_file/") and \
                self.path.endswith("/?format=json"):
            # e.g. /api/v1/mydata_dataset_file/12345/?format=json
            match = re.match(r"^/api/v1/mydata_dataset_file/(\d+)/\?format=json$", self.path)
            if match:
                dataFileId = match.groups()[0]
                replicaId = dataFileId
            else:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {
                    "error_message":
                    "Missing DataFile ID "
                    "in mydata_dataset_file GET query"
                }
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            datafileJson = {
                "id": dataFileId,
                "replicas": [
                    {
                        "id": replicaId,
                        "datafile": "/api/v1/dataset_file/%s/" % dataFileId
                    }
                ],
            }
            self.wfile.write(json.dumps(datafileJson))
        elif self.path.startswith("/api/v1/mydata_replica/") and \
                self.path.endswith("/?format=json"):
            # e.g. /api/v1/mydata_replica/12345/?format=json
            match = re.match(r"^/api/v1/mydata_replica/(\d+)/\?format=json$", self.path)
            if match:
                replicaId = match.groups()[0]
            else:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {
                    "error_message":
                    "Missing DFO ID "
                    "in mydata_replica GET query"
                }
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            replicaJson = {
                "id": replicaId,
                "size": 1024
            }
            self.wfile.write(json.dumps(replicaJson))
        elif self.path.startswith("/api/v1/dataset_file") and "verify" in self.path:
            # e.g. /api/v1/dataset_file/1/verify/
            match = re.match(r"^/api/v1/dataset_file/([0-9]+)/verify/$", self.path)
            if not match:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {
                    "error_message":
                    "Missing datafile ID in datafile verify query"
                }
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(200)
            self.end_headers()
            return
        elif self.path == "/about/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html><head><title>About FakeMyTardisServer</title></head>")
            self.wfile.write("<body><h2>About FakeMyTardisServer</h2>")
            self.wfile.write("</body></html>")
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html><head><title>FakeMyTardisServer</title></head>")
            self.wfile.write("<body><h2>FakeMyTardisServer</h2>")
            self.wfile.write("</body></html>")
        else:
            raise Exception("FakeMyTardis Server doesn't know how to respond "
                            "to GET: %s" % self.path)

    def do_POST(self):  # pylint: disable=invalid-name
        """
        Respond to a POST request
        """
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        if self.path.startswith("/api/v1/"):
            authorized = False
            authorization = self.headers.getheader("Authorization", "")
            match = re.match(r"^ApiKey (\S+):(\S+)$", authorization)
            if match:
                _ = urllib.unquote(match.groups()[0])  # username
                apiKey = urllib.unquote(match.groups()[1])  # API key
                if apiKey != "invalid":
                    authorized = True
            if not authorized:
                self.send_response(401)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("<html><head><title>"
                                 "FakeMyTardisServer API - Unauthorized"
                                 "</title></head>")
                self.wfile.write("<body><h2>Unauthorized</h2>")
                self.wfile.write("</body></html>")
                return

        length = int(self.headers['Content-Length'])
        ctype, _ = cgi.parse_header(self.headers.getheader('content-type'))
        if ctype == 'multipart/form-data':
            form = \
                cgi.FieldStorage(
                    fp=self.rfile, headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST',
                             'CONTENT_TYPE': self.headers['Content-Type']})
            postData = form['json_data']
        else:
            postData = json.loads(self.rfile.read(length))

        if self.path == "/api/v1/mydata_dataset_file/" or \
                self.path == "/api/v1/dataset_file/":
            self.send_response(201)
            self.send_header("Content-type", "text/html")
            self.datafileIdAutoIncrement += 1
            self.send_header("location",
                             "/api/v1/dataset_file/%d/"
                             % self.datafileIdAutoIncrement)
            self.end_headers()

            if ctype == 'multipart/form-data':
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
                self.wfile.write(tempUrl)
        elif self.path == "/api/v1/mydata_experiment/":
            if "Request 404 from Fake MyTardis Server" in postData['title']:
                self.send_response(404)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                errorJson = {}
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(201)
            self.send_header("Content-type", "text/html")
            self.end_headers()
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
            self.wfile.write(json.dumps(experimentJson))
        elif self.path == "/api/v1/objectacl/":
            self.send_response(201)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            objectaclJson = {
            }
            self.wfile.write(json.dumps(objectaclJson))
        elif self.path == "/api/v1/dataset/":
            self.send_response(201)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            experimentResourceUri = postData['experiments'][0]
            experimentId = experimentResourceUri.split("/")[-2]
            description = postData['description']
            datasetJson = {
                "description": description,
                "directory": "",
                "experiments": [
                    "/api/v1/experiment/%s/" % experimentId
                ],
                "id": 4457,
                "immutable": False,
                "instrument": {
                    "facility": {
                        "id": 2,
                        "manager_group": {
                            "id": 2,
                            "name": "test_facility_managers",
                            "resource_uri": "/api/v1/group/2/"
                        },
                        "name": "Test Facility",
                        "resource_uri": "/api/v1/facility/2/"
                    },
                    "id": 31,
                    "name": "Test Instrument",
                    "resource_uri": "/api/v1/instrument/31/"
                },
                "parameter_sets": [],
                "resource_uri": "/api/v1/dataset/4457/"
            }
            self.wfile.write(json.dumps(datasetJson))
        elif self.path == "/api/v1/instrument/":
            self.send_response(201)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            name = postData['name']
            instrumentJson = {
                "id": 32,
                "name": name,
                "facility": {
                    "id": 2,
                    "manager_group": {
                        "id": 2,
                        "name": "test_facility_managers",
                        "resource_uri": "/api/v1/group/2/"
                    },
                    "name": "Test Facility",
                    "resource_uri": "/api/v1/facility/2/"
                },
                "resource_uri": "/api/v1/instrument/32/"
            }
            self.wfile.write(json.dumps(instrumentJson))
        else:
            raise Exception("FakeMyTardis Server doesn't know how to respond "
                            "to POST: %s" % self.path)

    def do_PUT(self):  # pylint: disable=invalid-name
        """
        Respond to a PUT request
        """
        if self.path.startswith("/api/v1/mydata_uploader/"):
            match = re.match(r"^/api/v1/mydata_uploader/(\S+)/$", self.path)
            if match:
                uploaderId = match.groups()[0]
            else:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                errorJson = {"error_message": "Missing UUID in GET query"}
                self.wfile.write(json.dumps(errorJson))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            uploadersJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
                    {
                        "id": uploaderId,
                        "name": "Test Instrument",
                        "instruments": [
                            {
                                "id": 31,
                                "name": "Test Instrument",
                                "facility": {
                                    "id": 2,
                                    "manager_group": {
                                        "id": 2,
                                        "name": "test_facility_managers",
                                        "resource_uri": "/api/v1/group/2/"
                                    },
                                    "name": "Test Facility",
                                    "resource_uri": "/api/v1/facility/2/"
                                },
                                "resource_uri": "/api/v1/instrument/31/"
                            }
                        ],
                        "resource_uri": "/api/v1/mydata_uploader/25/",
                    }
                ]
            }
            self.wfile.write(json.dumps(uploadersJson))
        elif self.path.startswith("/api/v1/instrument/17/"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            instrumentsJson = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 1
                },
                "objects": [
                    {
                        "id": 31,
                        "name": "Renamed Instrument",
                        "facility": {
                            "id": 2,
                            "manager_group": {
                                "id": 2,
                                "name": "test_facility_managers",
                                "resource_uri": "/api/v1/group/2/"
                            },
                            "name": "Test Facility",
                            "resource_uri": "/api/v1/facility/2/"
                        },
                        "resource_uri": "/api/v1/instrument/17/"
                    }
                ]
            }
            self.wfile.write(json.dumps(instrumentsJson))
        else:
            raise Exception("FakeMyTardis Server doesn't know how to respond "
                            "to PUT: %s" % self.path)

    def do_PATCH(self):  # pylint: disable=invalid-name
        """
        Respond to a PATCH request
        """
        self.send_response(202)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        """
        Supressing logging of HTTP requests to STDERR.
        """
        if DEBUG:
            return BaseHTTPServer.BaseHTTPRequestHandler.log_message(
                self, format, *args)
        else:
            return

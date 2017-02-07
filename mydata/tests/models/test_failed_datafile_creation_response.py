"""
Test ability to respond to failed DataFile creation.
"""
import unittest

import requests

from mydata.controllers.uploads import UploadDatafileRunnable
from mydata.utils.exceptions import Unauthorized
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import InternalServerError


class FailedDataFileCreationTester(unittest.TestCase):
    """
    Test ability to respond to failed DataFile creation.
    """
    def test_failed_datafile_creation_response(self):
        """
        Test ability to respond to failed DataFile creation.
        """
        response = requests.Response()
        response.status_code = 401
        dataFileName = "filename.dat"
        folderName = "folder1"
        myTardisUsername = "testuser1"
        try:
            raisedUnauthorized = False
            UploadDatafileRunnable.HandleFailedCreateDataFile(
                response, dataFileName, folderName, myTardisUsername)
        except Unauthorized:
            raisedUnauthorized = True
        finally:
            self.assertTrue(raisedUnauthorized)
        response.status_code = 404
        try:
            raisedDoesNotExist = False
            UploadDatafileRunnable.HandleFailedCreateDataFile(
                response, dataFileName, folderName, myTardisUsername)
        except DoesNotExist:
            raisedDoesNotExist = True
        finally:
            self.assertTrue(raisedDoesNotExist)
        response.status_code = 500
        try:
            raisedInternalServerError = False
            UploadDatafileRunnable.HandleFailedCreateDataFile(
                response, dataFileName, folderName, myTardisUsername)
        except InternalServerError:
            raisedInternalServerError = True
        finally:
            self.assertTrue(raisedInternalServerError)
        # pylint: disable=protected-access
        response._content = '{"error_message": "Failed to create DataFile."}'
        try:
            raisedInternalServerError = False
            UploadDatafileRunnable.HandleFailedCreateDataFile(
                response, dataFileName, folderName, myTardisUsername)
        except InternalServerError:
            raisedInternalServerError = True
        finally:
            self.assertTrue(raisedInternalServerError)

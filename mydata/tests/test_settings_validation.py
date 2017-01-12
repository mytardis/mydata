"""
Test ability to validate settings.
"""
import unittest
import tempfile
import os
import sys
import threading
import time
from BaseHTTPServer import HTTPServer

import requests

from mydata.models.settings import SettingsModel
from mydata.tests.fake_mytardis_server import FakeMyTardisHandler
from mydata.tests.utils import GetEphemeralPort


class SettingsValidationTester(unittest.TestCase):
    """
    Test ability to validate settings.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(SettingsValidationTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.settingsModel = None
        self.tempConfig = None
        self.tempFilePath = None

    def setUp(self):
        """
        If we're creating a wx application in the test, it's
        safest to do it in setUp, because we know that setUp
        will only be called once, so only one app will be created.
        """
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/testdataUsernameDataset_POST.cfg")
        self.settingsModel = SettingsModel(configPath=configPath, checkForUpdates=False)
        self.tempConfig = tempfile.NamedTemporaryFile()
        self.tempFilePath = self.tempConfig.name
        self.tempConfig.close()
        self.settingsModel.SetConfigPath(self.tempFilePath)
        self.StartFakeMyTardisServer()
        self.settingsModel.SetMyTardisUrl(
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort))
        self.settingsModel.SetDataDirectory(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "testdata", "testdataUsernameDataset"))
        self.settingsModel.SaveToDisk()

    def tearDown(self):
        if os.path.exists(self.tempFilePath):
            os.remove(self.tempFilePath)
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()

    def test_settings_validation(self):
        """
        Test ability to validate settings.
        """
        # pylint: disable=too-many-statements

        # Start fake MyTardis server:
        sys.stderr.write("Waiting for fake MyTardis server to start...\n")
        attempts = 0
        while True:
            try:
                attempts += 1
                requests.get(self.settingsModel.GetMyTardisUrl() + "/api/v1/?format=json",
                             timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (self.settingsModel.GetMyTardisUrl(),
                                       str(err)))

        # Let's populate some settings which will trigger warnings
        # when using MyData's Test Run feature:
        self.settingsModel.SetIgnoreOldDatasets(True)
        self.settingsModel.SetIgnoreNewFiles(True)
        self.settingsModel.SetUserFilter("*")
        self.settingsModel.SetDatasetFilter("*")
        self.settingsModel.SetExperimentFilter("*")
        self.settingsModel.SetUploadInvalidUserOrGroupFolders(False)
        settingsValidation = self.settingsModel.Validate(testRun=True)
        self.assertTrue(settingsValidation.IsValid())

        # Now let's make some settings invalid and test validation:

        # Test missing MyTardis URL.
        self.settingsModel.SetMyTardisUrl("")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "mytardis_url")

        # Test invalid MyTardis URL:
        self.settingsModel.SetMyTardisUrl("invalid://tardis.url")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "mytardis_url")
        self.settingsModel.SetMyTardisUrl(
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort))

        # Test invalid HTTP status code from MyTardis URL:
        self.settingsModel.SetMyTardisUrl(
            "http://%s:%s/request/http/code/401"
            % (self.fakeMyTardisHost, self.fakeMyTardisPort))
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "mytardis_url")
        self.settingsModel.SetMyTardisUrl(
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort))

        # Test invalid HTTP status code from MyTardis URL:
        self.settingsModel.SetMyTardisUrl(
            "http://%s:%s/request/http/code/500"
            % (self.fakeMyTardisHost, self.fakeMyTardisPort))
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "mytardis_url")
        self.settingsModel.SetMyTardisUrl(
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort))

        # Test missing Facility Name:
        self.settingsModel.SetFacilityName("")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "facility_name")
        self.settingsModel.SetFacilityName("Test Facility")

        # Test invalid Facility Name:
        self.settingsModel.SetFacilityName("Invalid Facility")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "facility_name")
        self.settingsModel.SetFacilityName("Test Facility")

        # Test missing Instrument Name:
        self.settingsModel.SetInstrumentName("")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "instrument_name")
        self.settingsModel.SetInstrumentName("Test Instrument")

        # Test missing Contact Name:
        self.settingsModel.SetContactName("")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "contact_name")
        self.settingsModel.SetContactName("Test User")

        # Test missing Contact Email:
        self.settingsModel.SetContactEmail("")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "contact_email")
        self.settingsModel.SetContactEmail("testuser@example.com")

        # Test invalid Contact Email:
        self.settingsModel.SetContactEmail("invalid.email_address")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "contact_email")
        self.settingsModel.SetContactEmail("testuser@example.com")

        # Test missing MyTardis Username:
        self.settingsModel.SetUsername("")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "username")
        self.settingsModel.SetUsername("testfacility")

        # Test missing MyTardis API Key:
        self.settingsModel.SetApiKey("")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "api_key")
        self.settingsModel.SetApiKey("????????")

        # Test globs validations for valid includes file:
        includesFileObj = tempfile.NamedTemporaryFile()
        includesFilePath = includesFileObj.name
        includesFileObj.close()
        with open(includesFilePath, 'w') as includesFile:
            includesFile.write("*.tif\n")
        self.settingsModel.SetUseIncludesFile(True)
        self.settingsModel.SetIncludesFile(includesFilePath)
        settingsValidation = self.settingsModel.Validate(testRun=True)
        self.assertTrue(settingsValidation.IsValid())
        os.remove(includesFilePath)

        # Test globs validation for non-existent includes file:
        self.settingsModel.SetUseIncludesFile(True)
        self.settingsModel.SetIncludesFile("/path/doesn't/exist")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "includes_file")

        # Test globs validation for includes file path which is
        # actually a directory:
        self.settingsModel.SetUseIncludesFile(True)
        self.settingsModel.SetIncludesFile(os.getcwd())
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "includes_file")

        # Test globs validation where checkbox is ticket for using
        # an includes file, but no includes file is specified:
        self.settingsModel.SetUseIncludesFile(True)
        self.settingsModel.SetIncludesFile("")
        settingsValidation = self.settingsModel.Validate()
        self.assertFalse(settingsValidation.IsValid())
        self.assertEqual(settingsValidation.GetField(), "includes_file")

        # Test "Test Run" warnings triggered when use_includes_file
        # and/or use_excludes_file are activated.  The warning should
        # appear in STDERR output of this test.
        self.settingsModel.SetUseIncludesFile(True)
        self.settingsModel.SetUseExcludesFile(True)
        self.settingsModel.Validate(testRun=True)

        # Test "Test Run" warnings triggered when use_includes_file
        # and/or use_excludes_file are activated.  The warning should
        # appear in STDERR output of this test.
        self.settingsModel.SetUseIncludesFile(False)
        self.settingsModel.SetUseExcludesFile(True)
        self.settingsModel.Validate(testRun=True)

    def StartFakeMyTardisServer(self):
        """
        Start fake MyTardis server.
        """
        self.fakeMyTardisPort = GetEphemeralPort()
        self.httpd = HTTPServer((self.fakeMyTardisHost, self.fakeMyTardisPort),
                                FakeMyTardisHandler)

        def FakeMyTardisServer():
            """ Run fake MyTardis server """
            self.httpd.serve_forever()
        self.fakeMyTardisServerThread = \
            threading.Thread(target=FakeMyTardisServer,
                             name="FakeMyTardisServerThread")
        self.fakeMyTardisServerThread.start()

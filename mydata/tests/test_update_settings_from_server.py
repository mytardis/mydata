"""
Test ability to update settings from server.
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


class UpdatedSettingsTester(unittest.TestCase):
    """
    Test ability to update settings from server.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(UpdatedSettingsTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisUrl = None
        self.fakeMyTardisServerThread = None
        self.settingsModel = None
        self.tempConfig = None
        self.tempFilePath = None

    def setUp(self):
        """
        Set up for test.
        """
        self.configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/testdataUsernameDataset_POST.cfg")
        self.settingsModel = SettingsModel(configPath=self.configPath,
                                           checkForUpdates=False)
        self.tempConfig = tempfile.NamedTemporaryFile()
        self.tempFilePath = self.tempConfig.name
        self.tempConfig.close()
        self.settingsModel.SetConfigPath(self.tempFilePath)
        self.StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        self.WaitForFakeMyTardisServerToStart()
        self.settingsModel.SetMyTardisUrl(self.fakeMyTardisUrl)
        self.settingsModel.SetDataDirectory(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "testdata", "testdataUsernameDataset"))
        self.settingsModel.SaveToDisk()

    def tearDown(self):
        """
        Clean up after test.
        """
        if os.path.exists(self.tempFilePath):
            os.remove(self.tempFilePath)
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()

    def test_update_settings_from_server(self):
        """
        Test ability to update settings from server.
        """
        self.settingsModel.LoadSettings(checkForUpdates=True)
        self.assertEqual(self.settingsModel.GetContactName(), "Someone Else")
        self.assertFalse(self.settingsModel.ValidateFolderStructure())
        self.assertEqual(self.settingsModel.GetMaxVerificationThreads(), 2)
        self.assertEqual(str(self.settingsModel.GetScheduledDate()),
                         "2020-01-01")
        self.assertEqual(str(self.settingsModel.GetScheduledTime()),
                         "09:00:00")

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

    def WaitForFakeMyTardisServerToStart(self):
        """
        Wait for fake MyTardis server to start.
        """
        sys.stderr.write("Waiting for fake MyTardis server to start...\n")
        attempts = 0
        while True:
            try:
                attempts += 1
                requests.get(self.fakeMyTardisUrl +
                             "/api/v1/?format=json", timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (self.fakeMyTardisUrl, str(err)))

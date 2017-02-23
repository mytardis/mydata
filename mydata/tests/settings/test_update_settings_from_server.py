"""
Test ability to update settings from server.
"""
import unittest
import tempfile
import os

from mydata.models.settings import SettingsModel
from mydata.models.settings.serialize import LoadSettings
from mydata.models.settings.serialize import SaveSettingsToDisk
from mydata.tests.utils import StartFakeMyTardisServer
from mydata.tests.utils import WaitForFakeMyTardisServerToStart


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
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = SettingsModel(configPath=configPath,
                                           checkForUpdates=False)
        self.tempConfig = tempfile.NamedTemporaryFile()
        self.tempFilePath = self.tempConfig.name
        self.tempConfig.close()
        self.settingsModel.configPath = self.tempFilePath
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        WaitForFakeMyTardisServerToStart(self.fakeMyTardisUrl)
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        self.settingsModel.general.dataDirectory = dataDirectory
        SaveSettingsToDisk(self.settingsModel)

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

        For the purpose of testing, the updated values are hard-coded in
        mydata/tests/fake_mytardis_server.py
        """
        LoadSettings(self.settingsModel, checkForUpdates=True)
        self.assertEqual(self.settingsModel.general.contactName, "Someone Else")
        self.assertFalse(self.settingsModel.advanced.validateFolderStructure)
        self.assertEqual(self.settingsModel.miscellaneous.maxVerificationThreads, 2)
        self.assertEqual(str(self.settingsModel.schedule.scheduledDate),
                         "2020-01-01")
        self.assertEqual(str(self.settingsModel.schedule.scheduledTime),
                         "09:00:00")

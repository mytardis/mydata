"""
Test ability to detect invalid email addresses in the Email / Dataset structure.
"""
import os
import unittest

import wx

from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import InvalidSettings
from ..utils import StartFakeMyTardisServer
from ..utils import WaitForFakeMyTardisServerToStart


class ScanFoldersTester(unittest.TestCase):
    """
    Test ability to detect invalid email addresses in the Email / Dataset structure.
    """
    def __init__(self, *args, **kwargs):
        super(ScanFoldersTester, self).__init__(*args, **kwargs)
        self.app = None
        self.frame = None
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None

    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title='ScanFoldersTester')
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()

    def tearDown(self):
        self.frame.Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()

    def test_scan_folders(self):
        """
        Test ability to detect invalid email addresses in the Email / Dataset structure.
        """
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches

        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataInvalidEmailDataset.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataInvalidEmailDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        WaitForFakeMyTardisServerToStart(settingsModel.general.myTardisUrl)
        with self.assertRaises(InvalidSettings):
            ValidateSettings(settingsModel)

"""
Test ability to scan the Email / Experiment / Dataset folder structure.
"""
import os
import unittest

import wx

from ...events import MYDATA_EVENTS
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.folders import FoldersModel
from ...dataviewmodels.users import UsersModel
from ...dataviewmodels.groups import GroupsModel
from ..utils import StartFakeMyTardisServer
from ..utils import WaitForFakeMyTardisServerToStart


class ScanEmailExpDatasetTester(unittest.TestCase):
    """
    Test ability to scan the Email / Experiment / Dataset folder structure.
    """
    def __init__(self, *args, **kwargs):
        super(ScanEmailExpDatasetTester, self).__init__(*args, **kwargs)
        self.app = None
        self.frame = None
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None

    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title='ScanEmailExpDatasetTester')
        MYDATA_EVENTS.InitializeWithNotifyWindow(self.frame)
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()

    def tearDown(self):
        self.frame.Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()

    def test_scan_folders(self):
        """
        Test ability to scan the Email / Experiment / Dataset folder structure.
        """
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches

        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataEmailExpDataset.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataEmailExpDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        WaitForFakeMyTardisServerToStart(settingsModel.general.myTardisUrl)
        ValidateSettings(settingsModel)
        usersModel = UsersModel(settingsModel)
        groupsModel = GroupsModel(settingsModel)
        foldersModel = FoldersModel(usersModel, groupsModel, settingsModel)

        def IncrementProgressDialog():
            """
            Callback for ScanFolders.
            """
            pass

        def ShouldAbort():
            """
            Callback for ScanFolders.
            """
            return False

        foldersModel.ScanFolders(IncrementProgressDialog, ShouldAbort)
        self.assertEqual(sorted(usersModel.GetValuesForColname("Username")),
                         ["testuser1", "testuser2"])

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).GetFolder())
        self.assertEqual(sorted(folders), ["Birds", "Flowers"])

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).GetNumFiles()
        self.assertEqual(numFiles, 5)

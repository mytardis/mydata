"""
Test ability to open folders view.
"""
import unittest
import tempfile
import os

import wx

from ...models.folder import FolderModel
from ...models.user import UserModel
from ...dataviewmodels.folders import FoldersModel
from ...views.folders import FoldersView

from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...events import MYDATA_EVENTS
from ..utils import StartFakeMyTardisServer
from ..utils import WaitForFakeMyTardisServerToStart


class FoldersViewTester(unittest.TestCase):
    """
    Test ability to open folders view.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(FoldersViewTester, self).__init__(*args, **kwargs)
        self.app = None
        self.frame = None
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None

    def setUp(self):
        self.app = wx.App(redirect=False)
        self.frame = wx.Frame(None, title='FoldersViewTester')
        MYDATA_EVENTS.InitializeWithNotifyWindow(self.frame)
        self.usersModel = None
        self.groupsModel = None
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
        self.settingsModel.general.myTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        self.settingsModel.general.dataDirectory = \
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "../testdata", "testdataUsernameDataset")
        SaveSettingsToDisk(self.settingsModel)
        self.foldersModel = FoldersModel(self.usersModel, self.groupsModel,
                                         self.settingsModel)
        self.foldersView = FoldersView(self.frame, foldersModel=self.foldersModel)

    def test_folders_view(self):
        """
        Test ability to open folders view.
        """
        WaitForFakeMyTardisServerToStart(self.settingsModel.general.myTardisUrl)
        testuser1 = UserModel.GetUserByUsername(self.settingsModel, "testuser1")
        dataViewId = 1
        folder = "Flowers"
        location = "/path/to/testuser1/"
        userFolderName = "testuser1"
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, folder, location,
                        userFolderName, groupFolderName, testuser1,
                        self.settingsModel)
        self.foldersModel.AddRow(folderModel)
        self.assertEqual(self.foldersModel.GetValueByRow(0, 1), "Flowers")
        self.assertEqual(self.foldersModel.GetRowCount(), 1)
        self.assertEqual(self.foldersModel.GetUnfilteredRowCount(), 1)
        self.assertEqual(self.foldersModel.GetFilteredRowCount(), 0)
        folder = "Birds"
        folderModel = \
            FolderModel(dataViewId, folder, location,
                        userFolderName, groupFolderName, testuser1,
                        self.settingsModel)
        self.foldersModel.AddRow(folderModel)
        self.assertEqual(self.foldersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.foldersModel.GetFilteredRowCount(), 0)
        self.foldersModel.Filter("Flowers")
        self.assertEqual(self.foldersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.foldersModel.GetFilteredRowCount(), 1)
        self.foldersModel.Filter("")
        self.assertEqual(self.foldersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.foldersModel.GetFilteredRowCount(), 0)
        self.foldersModel.DeleteAllRows()
        self.assertEqual(self.foldersModel.GetUnfilteredRowCount(), 0)
        self.assertEqual(self.foldersModel.GetFilteredRowCount(), 0)

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()
        if os.path.exists(self.tempFilePath):
            os.remove(self.tempFilePath)

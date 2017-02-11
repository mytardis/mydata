"""
Test ability to open folders view.
"""
import unittest
import tempfile
import os
import sys
import time
import threading
from BaseHTTPServer import HTTPServer

import requests
import wx

from mydata.models.folder import FolderModel
from mydata.models.user import UserModel
from mydata.dataviewmodels.folders import FoldersModel
from mydata.views.folders import FoldersView

from mydata.models.settings import SettingsModel
from mydata.events import MYDATA_EVENTS
from mydata.tests.fake_mytardis_server import FakeMyTardisHandler
from mydata.tests.utils import GetEphemeralPort


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
        self.settingsModel.SetConfigPath(self.tempFilePath)
        self.StartFakeMyTardisServer()
        self.settingsModel.SetMyTardisUrl(
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort))
        self.settingsModel.SetDataDirectory(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "../testdata", "testdataUsernameDataset"))
        self.settingsModel.SaveToDisk()
        self.foldersModel = FoldersModel(self.usersModel, self.groupsModel,
                                         self.settingsModel)
        self.foldersView = FoldersView(self.frame, foldersModel=self.foldersModel)

    def test_folders_view(self):
        """
        Test ability to open folders view.
        """
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

"""
Test ability to scan the Username / MyTardis / Experiment / Dataset folder
structure.
"""
import os
import sys
import time
import logging
import subprocess
import unittest

import requests
import wx

from mydata.models.settings import SettingsModel
from mydata.dataviewmodels.folders import FoldersModel
from mydata.dataviewmodels.users import UsersModel
from mydata.dataviewmodels.groups import GroupsModel

logger = logging.getLogger(__name__)


class ScanUserMyTardisExpDatasetTester(unittest.TestCase):
    """
    Test ability to scan the Username / MyTardis / Experiment / Dataset folder
    structure.
    """
    def __init__(self, *args, **kwargs):
        super(ScanUserMyTardisExpDatasetTester, self).__init__(*args, **kwargs)
        self.fakeMyTardisServerProcess = None

    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title='ScanUserMyTardisExpDatasetTester')
        self.StartFakeMyTardisServer()

    def tearDown(self):
        self.frame.Destroy()
        self.fakeMyTardisServerProcess.terminate()

    def test_scan_folders(self):
        """
        Test ability to scan the Username / MyTardis / Experiment / Dataset
        folder structure.
        """
        # pylint: disable=no-self-use
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches

        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/testdataUserMyTardisExpDataset.cfg")
        settingsModel = SettingsModel(pathToTestConfig)
        settingsModel.SetDataDirectory(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "testdata", "testdataUserMyTardisExpDataset"))
        sys.stderr.write("Waiting for fake MyTardis server to start...\n")
        attempts = 0
        while True:
            try:
                attempts += 1
                requests.get(settingsModel.GetMyTardisUrl() +
                             "/api/v1/?format=json", timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (settingsModel.GetMyTardisUrl(),
                                       str(err)))

        settingsValidation = settingsModel.Validate()
        assert settingsValidation.IsValid()
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
        assert sorted(usersModel.GetValuesForColname("Username")) == \
            ["testuser1", "testuser2"]

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).GetFolder())
        assert sorted(folders) == ["Birds", "Flowers"]

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).GetNumFiles()
        assert numFiles == 5

    def StartFakeMyTardisServer(self):
        """
        Start fake MyTardis server.
        """
        os.environ['PYTHONPATH'] = os.path.realpath(".")
        self.fakeMyTardisServerProcess = \
            subprocess.Popen([sys.executable,
                              "mydata/tests/fake_mytardis_server.py"],
                             env=os.environ)


if __name__ == '__main__':
    unittest.main()

"""
Test ability to scan the Username / MyTardis / Experiment / Dataset folder
structure.
"""
import os

from .. import MyDataTester
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.folders import FoldersModel
from ...dataviewmodels.users import UsersModel
from ...dataviewmodels.groups import GroupsModel


class ScanUserMyTardisExpDatasetTester(MyDataTester):
    """
    Test ability to scan the Username / MyTardis / Experiment / Dataset folder
    structure.
    """
    def setUp(self):
        super(ScanUserMyTardisExpDatasetTester, self).setUp()
        super(ScanUserMyTardisExpDatasetTester, self).InitializeAppAndFrame(
            'ScanUserMyTardisExpDatasetTester')

    def test_scan_folders(self):
        """
        Test ability to scan the Username / MyTardis / Experiment / Dataset
        folder structure.
        """
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUserMyTardisExpDataset.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUserMyTardisExpDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
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
            folders.append(foldersModel.GetFolderRecord(row).folder)
        self.assertEqual(sorted(folders), ["Birds", "Flowers"])

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).GetNumFiles()
        self.assertEqual(numFiles, 5)

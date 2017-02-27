"""
Test ability to scan folders with the Email / Dataset structure.
"""
import os

from .. import MyDataTester
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.folders import FoldersModel
from ...dataviewmodels.users import UsersModel
from ...dataviewmodels.groups import GroupsModel


class ScanFoldersTester(MyDataTester):
    """
    Test ability to scan folders with the Email / Dataset structure.
    """
    def setUp(self):
        super(ScanFoldersTester, self).setUp()
        super(ScanFoldersTester, self).InitializeAppAndFrame(
            title='ScanFoldersTester')

    def test_scan_folders(self):
        """
        Test ability to scan folders with the Email / Dataset structure.
        """
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataEmailDataset.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataEmailDataset")
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

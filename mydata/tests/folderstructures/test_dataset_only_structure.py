"""
Test ability to scan the Dataset folder structure.
"""
import os

from ...settings import SETTINGS
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.folders import FoldersModel
from ...dataviewmodels.users import UsersModel
from ...dataviewmodels.groups import GroupsModel
from .. import MyDataScanFoldersTester


class ScanDatasetTester(MyDataScanFoldersTester):
    """
    Test ability to scan the Dataset folder structure.
    """
    def setUp(self):
        super(ScanDatasetTester, self).setUp()
        super(ScanDatasetTester, self).InitializeAppAndFrame(
            'ScanDatasetTester')

    def test_scan_folders(self):
        """
        Test ability to scan the Dataset folder structure.
        """
        pathToTestConfig = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataDataset.cfg"))
        self.assertTrue(os.path.exists(pathToTestConfig))
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataDataset"))
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        ValidateSettings()
        usersModel = UsersModel()
        groupsModel = GroupsModel()
        foldersModel = FoldersModel(usersModel, groupsModel)
        foldersModel.ScanFolders(
            MyDataScanFoldersTester.IncrementProgressDialog,
            MyDataScanFoldersTester.ShouldAbort)

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).folderName)
        self.assertEqual(sorted(folders), ["Birds", "Flowers"])

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).GetNumFiles()
        self.assertEqual(numFiles, 5)

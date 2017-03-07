"""
Test ability to scan the User Group / Instrument / Full Name / Dataset folder structure.
"""
import os

from ...settings import SETTINGS
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...models.settings.validation import CheckStructureAndCountDatasets
from ...dataviewmodels.folders import FoldersModel
from ...dataviewmodels.users import UsersModel
from ...dataviewmodels.groups import GroupsModel
from .. import MyDataScanFoldersTester


class ScanUserGroupInstrumentTester(MyDataScanFoldersTester):
    """
    Test ability to scan the User Group / Instrument / Full Name / Dataset folder structure.
    """
    def setUp(self):
        super(ScanUserGroupInstrumentTester, self).setUp()
        super(ScanUserGroupInstrumentTester, self).InitializeAppAndFrame(
            'ScanUserGroupInstrumentTester')

    def test_scan_folders(self):
        """
        Test ability to scan the User Group / Instrument / Full Name / Dataset folder structure.
        """
        pathToTestConfig = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataGroupInstrument.cfg"))
        self.assertTrue(os.path.exists(pathToTestConfig))
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataGroupInstrument"))
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        datasetCount = CheckStructureAndCountDatasets()
        self.assertEqual(datasetCount, 8)
        ValidateSettings()
        usersModel = UsersModel()
        groupsModel = GroupsModel()
        foldersModel = FoldersModel(usersModel, groupsModel)
        foldersModel.ScanFolders(
            MyDataScanFoldersTester.IncrementProgressDialog,
            MyDataScanFoldersTester.ShouldAbort)
        self.assertEqual(sorted(groupsModel.GetValuesForColname("Full Name")),
                         ["TestFacility-Group1", "TestFacility-Group2"])

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).folderName)
        self.assertEqual(sorted(folders), [
            'Dataset 001', 'Dataset 002', 'Dataset 003', 'Dataset 004',
            'Dataset 005', 'Dataset 006', 'Dataset 007', 'Dataset 008'])

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).GetNumFiles()
        self.assertEqual(numFiles, 8)

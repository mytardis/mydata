"""
Test ability to scan the User Group / Instrument / Full Name / Dataset folder structure.
"""
import os

from .. import MyDataTester
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...models.settings.validation import CheckStructureAndCountDatasets
from ...dataviewmodels.folders import FoldersModel
from ...dataviewmodels.users import UsersModel
from ...dataviewmodels.groups import GroupsModel


class ScanUserGroupInstrumentTester(MyDataTester):
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
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataGroupInstrument.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataGroupInstrument")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        datasetCount = CheckStructureAndCountDatasets(settingsModel)
        self.assertEqual(datasetCount, 8)
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
        self.assertEqual(sorted(groupsModel.GetValuesForColname("Full Name")),
                         ["TestFacility-Group1", "TestFacility-Group2"])

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).GetFolder())
        self.assertEqual(sorted(folders), [
            'Dataset 001', 'Dataset 002', 'Dataset 003', 'Dataset 004',
            'Dataset 005', 'Dataset 006', 'Dataset 007', 'Dataset 008'])

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).GetNumFiles()
        self.assertEqual(numFiles, 8)

"""
Test ability to upload files at the Experiment level.
"""
import os

from ...settings import SETTINGS
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.folders import FoldersModel
from ...dataviewmodels.users import UsersModel
from ...dataviewmodels.groups import GroupsModel
from .. import MyDataScanFoldersTester


class UploadExpFilesTester(MyDataScanFoldersTester):
    """
    Test ability to upload files at the Experiment level.
    """
    def setUp(self):
        super(UploadExpFilesTester, self).setUp()
        super(UploadExpFilesTester, self).InitializeAppAndFrame(
            'UploadExpFilesTester')

    def test_upload_exp_files(self):
        """
        Test ability to upload files at the Experiment level.
        """
        # pylint: disable=too-many-locals
        pathToTestConfig = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataExpDatasetExpFiles.cfg"))
        self.assertTrue(os.path.exists(pathToTestConfig))
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataExpDatasetExpFiles"))
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
        self.assertEqual(sorted(folders),
                         ["Birds", "Flowers",
                          "__EXPERIMENT_FILES__",
                          "__EXPERIMENT_FILES__"])

        totalNumFiles = 0
        foundExpFilename = False
        for row in range(foldersModel.GetRowCount()):
            folderModel = foldersModel.GetFolderRecord(row)
            numFiles = folderModel.GetNumFiles()
            totalNumFiles += numFiles
            for fileIndex in range(numFiles):
                if folderModel.GetDataFileName(fileIndex) == "exp_file1.txt":
                    foundExpFilename = True
        self.assertEqual(totalNumFiles, 7)
        self.assertTrue(foundExpFilename)

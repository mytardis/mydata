"""
Test ability to upload files at the Experiment level.
"""
import os

from .. import MyDataTester
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.folders import FoldersModel
from ...dataviewmodels.users import UsersModel
from ...dataviewmodels.groups import GroupsModel


class UploadExpFilesTester(MyDataTester):
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
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataExpDatasetExpFiles.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataExpDatasetExpFiles")
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

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).folder)
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

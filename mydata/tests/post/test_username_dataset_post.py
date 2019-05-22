"""
Test scanning the Username / Dataset structure and upload using POST.
"""
import sys

from ...settings import SETTINGS
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...dataviewmodels.uploads import UploadsModel
from ...dataviewmodels.verifications import VerificationsModel
from ...controllers.folders import FoldersController
from .. import MyDataScanFoldersTester
from .. import InitializeModels


class ScanUsernameDatasetPostTester(MyDataScanFoldersTester):
    """
    Test scanning the Username / Dataset structure and upload using POST.
    """
    def test_scan_folders(self):
        """Test scanning the Username / Dataset structure and upload using POST.
        """
        # pylint: disable=too-many-statements,too-many-locals
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        ValidateSettings()
        InitializeModels()
        self.assertTrue(SETTINGS.advanced.uploadInvalidUserOrGroupFolders)
        foldersModel = DATAVIEW_MODELS['folders']
        foldersModel.ScanFolders(MyDataScanFoldersTester.ProgressCallback)
        usersModel = DATAVIEW_MODELS['users']
        self.assertEqual(
            sorted(usersModel.GetValuesForColname("Username")),
            ['INVALID_USER', 'testuser1', 'testuser2'])

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).folderName)
        self.assertEqual(
            sorted(folders),
            ['Birds', 'Dataset with spaces', 'Flowers', 'InvalidUserDataset1'])

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).numFiles
        self.assertEqual(numFiles, 12)

        uploadsModel = UploadsModel()
        verificationsModel = VerificationsModel()
        DATAVIEW_MODELS['verifications'] = verificationsModel
        DATAVIEW_MODELS['uploads'] = uploadsModel
        self.app.foldersController = FoldersController(self.app.frame)
        self.app.foldersController.InitForUploads()
        for row in range(foldersModel.GetRowCount()):
            folderModel = foldersModel.GetFolderRecord(row)
            self.app.foldersController.StartUploadsForFolder(folderModel)
        self.app.foldersController.FinishedScanningForDatasetFolders()

        numVerificationsCompleted = verificationsModel.GetCompletedCount()
        uploadsCompleted = uploadsModel.GetCompletedCount()
        uploadsFailed = uploadsModel.GetFailedCount()
        uploadsProcessed = uploadsCompleted + uploadsFailed
        self.assertEqual(numVerificationsCompleted, numFiles)
        sys.stderr.write("\n")
        sys.stderr.write("%d/%d uploads completed.\n" % (uploadsCompleted, uploadsProcessed))
        if uploadsFailed > 0:
            sys.stderr.write("%d/%d uploads failed.\n" % (uploadsFailed, uploadsProcessed))
        self.assertEqual(uploadsCompleted, 8)

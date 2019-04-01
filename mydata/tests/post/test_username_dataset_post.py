"""
Test scanning the Username / Dataset structure and upload using POST.
"""
import sys
import threading
import time

import wx

from ...logs import logger
from ...settings import SETTINGS
from ...threads.flags import FLAGS
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...dataviewmodels.uploads import UploadsModel
from ...dataviewmodels.verifications import VerificationsModel
from ...controllers.folders import FoldersController
from ...models.upload import UploadStatus
from ..utils import Subtract
from .. import MyDataScanFoldersTester
from .. import InitializeModels


class ScanUsernameDatasetPostTester(MyDataScanFoldersTester):
    """
    Test scanning the Username / Dataset structure and upload using POST.
    """
    def test_scan_folders(self):
        """Test scanning the Username / Dataset structure and upload using POST
        """
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
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


        # Now let's test canceling the uploads:

        loggerOutput = logger.GetValue()
        def StartUploads():
            """
            Start Uploads worker
            """
            self.app.foldersController.InitForUploads()
            for row in range(foldersModel.GetRowCount()):
                folderModel = foldersModel.GetFolderRecord(row)
                self.app.foldersController.StartUploadsForFolder(folderModel)

        startUploadsThread = threading.Thread(
            target=StartUploads, name="StartUploads")
        # Do this synchronously to ensure that the completed flag is reset:
        self.app.foldersController.InitializeStatusFlags()
        startUploadsThread.start()
        sys.stderr.write("Waiting for uploads to start...\n")
        while uploadsModel.GetCount() == 0:
            time.sleep(0.05)
        while uploadsModel.rowsData[0].status == UploadStatus.NOT_STARTED:
            time.sleep(0.05)
        sys.stderr.write("\nCanceling uploads...\n")
        FLAGS.shouldAbort = True
        self.app.foldersController.ShutDownUploadThreads(event=wx.PyEvent())
        startUploadsThread.join()
        FLAGS.shouldAbort = False
        newLogs = Subtract(logger.GetValue(), loggerOutput)
        self.assertIn("Data scans and uploads were canceled.", newLogs)

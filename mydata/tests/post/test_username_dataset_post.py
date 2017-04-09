"""
Test scanning the Username / Dataset structure and upload using POST.
"""
import sys
import threading
import time

import wx

from ...logs import logger
from ...settings import SETTINGS
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.uploads import UploadsModel
from ...dataviewmodels.verifications import VerificationsModel
from ...views.dataview import MyDataDataView
from ...controllers.folders import FoldersController
from ...models.upload import UploadStatus
from ..utils import Subtract
from .. import MyDataScanFoldersTester


class ScanUsernameDatasetPostTester(MyDataScanFoldersTester):
    """
    Test scanning the Username / Dataset structure and upload using POST.
    """
    def setUp(self):
        super(ScanUsernameDatasetPostTester, self).setUp()
        super(ScanUsernameDatasetPostTester, self).InitializeAppAndFrame(
            'ScanUsernameDatasetPostTester')

    def test_scan_folders(self):
        """
        Test scanning the Username / Dataset structure and upload using POST.
        """
        # pylint: disable=too-many-locals
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        ValidateSettings()
        self.InitializeModels()
        self.assertTrue(SETTINGS.advanced.uploadInvalidUserOrGroupFolders)
        self.foldersModel.ScanFolders(
            MyDataScanFoldersTester.IncrementProgressDialog,
            MyDataScanFoldersTester.ShouldAbort)
        self.assertEqual(
            sorted(self.usersModel.GetValuesForColname("Username")),
            ['INVALID_USER', 'testuser1', 'testuser2'])

        folders = []
        for row in range(self.foldersModel.GetRowCount()):
            folders.append(self.foldersModel.GetFolderRecord(row).folderName)
        self.assertEqual(
            sorted(folders), ['Birds', 'Flowers', 'InvalidUserDataset1'])

        numFiles = 0
        for row in range(self.foldersModel.GetRowCount()):
            numFiles += self.foldersModel.GetFolderRecord(row).GetNumFiles()
        self.assertEqual(numFiles, 11)

        uploadsModel = UploadsModel()
        verificationsModel = VerificationsModel()
        foldersView = MyDataDataView(self.frame, self.foldersModel)
        foldersController = FoldersController(
            self.frame, self.foldersModel, foldersView, self.usersModel,
            verificationsModel, uploadsModel)

        foldersController.InitForUploads()
        for row in range(self.foldersModel.GetRowCount()):
            folderModel = self.foldersModel.GetFolderRecord(row)
            foldersController.StartUploadsForFolder(folderModel)
        foldersController.FinishedScanningForDatasetFolders()

        numVerificationsCompleted = verificationsModel.GetCompletedCount()
        uploadsCompleted = uploadsModel.GetCompletedCount()
        uploadsFailed = uploadsModel.GetFailedCount()
        uploadsProcessed = uploadsCompleted + uploadsFailed
        self.assertEqual(numVerificationsCompleted, numFiles)
        sys.stderr.write("\n")
        sys.stderr.write("%d/%d uploads completed.\n" % (uploadsCompleted, uploadsProcessed))
        if uploadsFailed > 0:
            sys.stderr.write("%d/%d uploads failed.\n" % (uploadsFailed, uploadsProcessed))
        self.assertEqual(uploadsCompleted, 7)


        # Now let's test canceling the uploads:

        loggerOutput = logger.loggerOutput.getvalue()
        def StartUploads():
            """
            Start Uploads worker
            """
            foldersController.InitForUploads()
            for row in range(self.foldersModel.GetRowCount()):
                folderModel = self.foldersModel.GetFolderRecord(row)
                foldersController.StartUploadsForFolder(folderModel)
            foldersController.FinishedScanningForDatasetFolders()

        startUploadsThread = threading.Thread(
            target=StartUploads, name="StartUploads")
        startUploadsThread.start()
        sys.stderr.write("Waiting for uploads to start...\n")
        while uploadsModel.GetCount() == 0:
            time.sleep(0.05)
        while uploadsModel.rowsData[0].status == UploadStatus.NOT_STARTED:
            time.sleep(0.05)
        sys.stderr.write("\nCanceling uploads...\n")
        foldersController.ShutDownUploadThreads(event=wx.PyEvent())
        startUploadsThread.join()
        logger.Flush()
        newLogs = Subtract(logger.loggerOutput.getvalue(), loggerOutput)
        self.assertIn("Data scans and uploads were canceled.", newLogs)

        # Simulate ConnectionError while trying to access MyTardis URL:
        sys.stderr.write(
            "\nAsking fake MyTardis server to shut down abruptly...\n")
        loggerOutput = logger.loggerOutput.getvalue()
        SETTINGS.general.myTardisUrl = \
            "%s/request/connectionerror/" % self.fakeMyTardisUrl
        event = wx.PyEvent()
        event.folderModel = self.foldersModel.GetFolderRecord(0)
        event.dataFileIndex = 0
        foldersController.UploadDatafile(event)
        logger.Flush()
        newLogs = Subtract(logger.loggerOutput.getvalue(), loggerOutput)
        # We should see some sort of connection error in the log, but we don't
        # know which one it will be.
        # Errno 10053 is a Winsock error: "Software caused connection abort"
        self.assertTrue(
            "urlopen error [Errno 32] Broken pipe" in newLogs or
            "BadStatusLine" in newLogs or
            "urlopen error [Errno 10053]" in newLogs)

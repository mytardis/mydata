"""
Test scanning the Username / Dataset structure and upload using POST.
"""
import os
import sys
import threading
import time

import wx

from ...logs import logger
from ...settings import SETTINGS
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.folders import FoldersModel
from ...dataviewmodels.users import UsersModel
from ...dataviewmodels.groups import GroupsModel
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
        pathToTestConfig = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg"))
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        SETTINGS.general.dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset"))
        ValidateSettings()
        usersModel = UsersModel()
        groupsModel = GroupsModel()
        foldersModel = FoldersModel(usersModel, groupsModel)
        self.assertTrue(SETTINGS.advanced.uploadInvalidUserOrGroupFolders)
        foldersModel.ScanFolders(
            MyDataScanFoldersTester.IncrementProgressDialog,
            MyDataScanFoldersTester.ShouldAbort)
        self.assertEqual(sorted(usersModel.GetValuesForColname("Username")),
                         ['INVALID_USER', 'testuser1', 'testuser2'])

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).folderName)
        self.assertEqual(
            sorted(folders), ['Birds', 'Flowers', 'InvalidUserDataset1'])

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).GetNumFiles()
        self.assertEqual(numFiles, 11)

        uploadsModel = UploadsModel()
        verificationsModel = VerificationsModel()
        foldersView = MyDataDataView(self.frame, foldersModel)
        foldersController = FoldersController(
            self.frame, foldersModel, foldersView, usersModel,
            verificationsModel, uploadsModel)

        foldersController.InitForUploads()
        for row in range(foldersModel.GetRowCount()):
            folderModel = foldersModel.GetFolderRecord(row)
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
            for row in range(foldersModel.GetRowCount()):
                folderModel = foldersModel.GetFolderRecord(row)
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
        newLogs = Subtract(logger.loggerOutput.getvalue(), loggerOutput)
        self.assertIn("Data scans and uploads were canceled.", newLogs)

        # Simulate ConnectionError while trying to access MyTardis URL:
        sys.stderr.write(
            "\nAsking fake MyTardis server to shut down abruptly...\n")
        loggerOutput = logger.loggerOutput.getvalue()
        SETTINGS.general.myTardisUrl = \
            "%s/request/connectionerror/" % self.fakeMyTardisUrl
        event = wx.PyEvent()
        event.folderModel = foldersModel.GetFolderRecord(0)
        event.dataFileIndex = 0
        foldersController.UploadDatafile(event)
        newLogs = Subtract(logger.loggerOutput.getvalue(), loggerOutput)
        self.assertTrue(
            "urlopen error [Errno 32] Broken pipe" in newLogs or
            "BadStatusLine" in newLogs)

"""
Test scanning the Username / Dataset structure and upload using POST.
"""
import os
import sys
import time
import subprocess
import unittest

import requests
import wx

from mydata.models.settings import SettingsModel
from mydata.dataviewmodels.folders import FoldersModel
from mydata.dataviewmodels.users import UsersModel
from mydata.dataviewmodels.groups import GroupsModel
from mydata.dataviewmodels.uploads import UploadsModel
from mydata.dataviewmodels.verifications import VerificationsModel
from mydata.views.folders import FoldersView
from mydata.controllers.folders import FoldersController
from mydata.models.upload import UploadStatus
if sys.platform.startswith("linux"):
    from mydata.linuxsubprocesses import StopErrandBoy

class ScanUsernameDatasetTester(unittest.TestCase):
    """
    Test scanning the Username / Dataset structure and upload using POST.
    """
    def __init__(self, *args, **kwargs):
        super(ScanUsernameDatasetTester, self).__init__(*args, **kwargs)
        self.fakeMyTardisServerProcess = None

    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title='ScanUsernameDatasetTester')
        self.StartFakeMyTardisServer()

    def tearDown(self):
        self.frame.Destroy()
        self.fakeMyTardisServerProcess.terminate()
        if sys.platform.startswith("linux"):
            StopErrandBoy()

    def test_scan_folders(self):
        """
        Test scanning the Username / Dataset structure and upload using POST.
        """
        # pylint: disable=no-self-use
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches

        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/testdataUsernameDataset_POST.cfg")
        settingsModel = SettingsModel(pathToTestConfig)
        settingsModel.SetDataDirectory(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "testdata", "testdataUsernameDataset"))
        sys.stderr.write("Waiting for fake MyTardis server to start...\n")
        attempts = 0
        while True:
            try:
                attempts += 1
                requests.get(settingsModel.GetMyTardisUrl() + "/api/v1/?format=json",
                             timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (settingsModel.GetMyTardisUrl(),
                                       str(err)))

        settingsValidation = settingsModel.Validate()
        assert settingsValidation.IsValid()
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
        assert sorted(usersModel.GetValuesForColname("Username")) == \
            ["testuser1", "testuser2"]

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).GetFolder())
        assert sorted(folders) == ["Birds", "Flowers"]

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).GetNumFiles()
        assert numFiles == 5

        uploadsModel = UploadsModel()
        verificationsModel = VerificationsModel()
        foldersView = FoldersView(self.frame, foldersModel)
        foldersController = \
            FoldersController(self.frame,
                              foldersModel,
                              foldersView,
                              usersModel,
                              verificationsModel,
                              uploadsModel,
                              settingsModel)

        foldersController.InitForUploads()
        for row in range(foldersModel.GetRowCount()):
            folderModel = foldersModel.GetFolderRecord(row)
            foldersController.StartUploadsForFolder(folderModel)
        foldersController.FinishedScanningForDatasetFolders()

        while True:
            numVerificationsCompleted = verificationsModel.GetCompletedCount()
            uploadsToBePerformed = uploadsModel.GetRowCount()
            uploadsCompleted = uploadsModel.GetCompletedCount()
            uploadsFailed = uploadsModel.GetFailedCount()
            uploadsProcessed = uploadsCompleted + uploadsFailed

            finishedVerificationCounting = True
            for folder in foldersController.finishedCountingVerifications:
                if not foldersController.finishedCountingVerifications[folder]:
                    finishedVerificationCounting = False

            if numVerificationsCompleted == numFiles \
                    and finishedVerificationCounting \
                    and uploadsProcessed == uploadsToBePerformed:
                break
            time.sleep(0.1)
        assert numVerificationsCompleted == numFiles

        # Verifications won't be able to trigger uploads via PostEvent,
        # because there is no running event loop, so we'll manually call
        # UploadDatafile for each datafile.

        uploadsToBePerformed = numVerificationsCompleted
        for i in range(numVerificationsCompleted):
            verificationModel = verificationsModel.verificationsData[i]
            folderModelId = verificationModel.GetFolderModelId()
            folderModel = foldersModel.GetFolderRecord(folderModelId-1)
            dataFileIndex = verificationModel.GetDataFileIndex()
            event = foldersController.didntFindDatafileOnServerEvent(
                foldersController=foldersController,
                folderModel=folderModel,
                dataFileIndex=dataFileIndex,
                verificationModel=verificationModel)
            foldersController.UploadDatafile(event)

        sys.stderr.write("Waiting for uploads to complete...\n")
        while True:
            uploadsCompleted = uploadsModel.GetCompletedCount()
            uploadsFailed = uploadsModel.GetFailedCount()
            uploadsProcessed = uploadsCompleted + uploadsFailed

            if uploadsProcessed == uploadsToBePerformed:
                break
            time.sleep(0.1)
        foldersController.ShutDownUploadThreads()

        sys.stderr.write("\n")
        sys.stderr.write("%d/%d uploads completed.\n" % (uploadsCompleted, uploadsProcessed))
        if uploadsFailed > 0:
            sys.stderr.write("%d/%d uploads failed.\n" % (uploadsFailed, uploadsProcessed))

        for i in range(uploadsProcessed):
            uploadModel = uploadsModel.uploadsData[i]
            if uploadModel.GetStatus() == UploadStatus.FAILED:
                sys.stderr.write(
                    "Upload failed for %s: %s\n" %
                    (uploadModel.GetFilename(),
                     uploadModel.GetMessage().strip()))
                if uploadModel.GetTraceback():
                    sys.stderr.write(uploadModel.GetTraceback())
        sys.stderr.write("\n")

        assert uploadsCompleted == numFiles

    def StartFakeMyTardisServer(self):
        """
        Start fake MyTardis server.
        """
        os.environ['PYTHONPATH'] = os.path.realpath(".")
        self.fakeMyTardisServerProcess = \
            subprocess.Popen([sys.executable,
                              "mydata/tests/fake_mytardis_server.py"],
                             env=os.environ)


if __name__ == '__main__':
    unittest.main()

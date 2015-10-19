"""
Test ability to scan folders.
"""
import unittest
import os
import sys
import time
import logging
import wx
import subprocess
import requests

from mydata.models.settings import SettingsModel
from mydata.dataviewmodels.folders import FoldersModel
from mydata.dataviewmodels.users import UsersModel
from mydata.dataviewmodels.groups import GroupsModel
from mydata.dataviewmodels.uploads import UploadsModel
from mydata.dataviewmodels.verifications import VerificationsModel
from mydata.views.folders import FoldersView
from mydata.controllers.folders import FoldersController
import mydata.utils.openssh as OpenSSH
from mydata.models.upload import UploadStatus
from mydata.utils.exceptions import PrivateKeyDoesNotExist

logger = logging.getLogger(__name__)


class ScanFoldersTester(unittest.TestCase):
    """
    Test ability to scan folders.
    """
    def __init__(self, *args, **kwargs):
        super(ScanFoldersTester, self).__init__(*args, **kwargs)
        self.fakeMyTardisServerProcess = None
        self.fakeSshServerProcess = None

    def setUp(self):
        self.app = wx.PySimpleApp()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title='ScanFoldersTester')
        self.StartFakeMyTardisServer()
        self.StartFakeSshServer()

    def tearDown(self):
        self.frame.Destroy()
        self.app.Destroy()
        self.fakeMyTardisServerProcess.terminate()
        self.fakeSshServerProcess.terminate()

    def test_scan_folders(self):
        """
        Test ability to scan folders.
        """
        # pylint: disable=no-self-use
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches

        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/testdata1.cfg")
        settingsModel = SettingsModel(pathToTestConfig)
        settingsModel.SetDataDirectory(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "testdata", "testdata1"))
        settingsModel.SetUseSshControlMasterIfAvailable(False)
        sys.stderr.write("Waiting for fake MyTardis server to start...\n")
        attempts = 0
        while True:
            try:
                attempts += 1
                requests.get(settingsModel.GetMyTardisUrl() + "/about/",
                             timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                sys.stderr.write(str(err) + "\n")
                time.sleep(0.1)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s"
                                    % settingsModel.GetMyTardisUrl())

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

        sys.stderr.write("Waiting for fake SSH server to start up...\n")
        username = "mydata"
        try:
            keyPair = OpenSSH.FindKeyPair("MyData")
        except PrivateKeyDoesNotExist:
            keyPair = OpenSSH.NewKeyPair("MyData")
        privateKeyFilePath = keyPair.GetPrivateKeyFilePath()
        host = "localhost"
        port = 2200
        while not OpenSSH.SshServerIsReady(username, privateKeyFilePath,
                                           host, port):
            time.sleep(0.1)

        foldersController.StartDataUploads()

        while True:
            numVerificationsCompleted = verificationsModel.GetCompletedCount()
            uploadsToBePerformed = uploadsModel.GetRowCount()
            uploadsCompleted = uploadsModel.GetCompletedCount()
            uploadsFailed = uploadsModel.GetFailedCount()
            uploadsProcessed = uploadsCompleted + uploadsFailed

            if numVerificationsCompleted == numFiles and \
                    foldersController.finishedCountingVerifications.isSet() \
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
            folderModel = verificationModel.GetFolderModel()
            dataFileIndex = verificationModel.GetDataFileIndex()
            event = foldersController.didntFindDatafileOnServerEvent(
                foldersController=foldersController,
                folderModel=folderModel,
                dataFileIndex=dataFileIndex,
                verificationModel=verificationModel)
            foldersController.UploadDatafile(event)

        sys.stderr.write("Waiting for uploads to complete...\n")
        logger.debug("Waiting for uploads to complete...")
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

    def StartFakeSshServer(self):
        """
        Start fake SSH/SCP server.
        """
        os.environ['PYTHONPATH'] = os.path.realpath(".")
        self.fakeSshServerProcess = \
            subprocess.Popen([sys.executable,
                              "mydata/tests/fake_ssh_server.py"],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             env=os.environ)


if __name__ == '__main__':
    unittest.main()

"""
Test ability to scan the Username / Dataset structure and upload using SCP.
"""
import os
import sys
import time
import unittest
import threading
import socket
import select
from BaseHTTPServer import HTTPServer

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
import mydata.utils.openssh as OpenSSH
from mydata.models.upload import UploadStatus
from mydata.utils.exceptions import PrivateKeyDoesNotExist
from mydata.tests.fake_mytardis_server import FakeMyTardisHandler
from mydata.tests.fake_ssh_server import ThreadedSshServer
from mydata.tests.utils import GetEphemeralPort
from mydata.events import MYDATA_EVENTS
if sys.platform.startswith("linux"):
    from mydata.linuxsubprocesses import StopErrandBoy


class ScanUsernameDatasetTester(unittest.TestCase):
    """
    Test ability to scan the Username / Dataset structure and upload using SCP.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(ScanUsernameDatasetTester, self).__init__(*args, **kwargs)
        self.app = None
        self.frame = None
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.fakeSshServerThread = None

    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title='ScanUsernameDatasetTester')
        MYDATA_EVENTS.InitializeWithNotifyWindow(self.frame)
        self.StartFakeMyTardisServer()
        # The fake SSH server needs to know the public
        # key so it can authenticate the test client.
        # So we need to ensure that the MyData keypair
        # is generated before starting the fake SSH server.
        try:
            self.keyPair = OpenSSH.FindKeyPair("MyDataTest")
        except PrivateKeyDoesNotExist:
            self.keyPair = OpenSSH.NewKeyPair("MyDataTest")
        self.StartFakeSshServer()

    def tearDown(self):
        self.keyPair.Delete()
        self.frame.Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()
        self.sshd.server_close()
        self.fakeSshServerThread.join()
        if sys.platform.startswith("linux"):
            StopErrandBoy()

    def test_scan_folders(self):
        """
        Test ability to scan the Username / Dataset structure and upload using SCP.
        """
        # pylint: disable=no-self-use
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches

        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/testdataUsernameDataset.cfg")
        settingsModel = SettingsModel(pathToTestConfig)
        settingsModel.SetDataDirectory(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "testdata", "testdataUsernameDataset"))
        settingsModel.SetMyTardisUrl(
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort))
        settingsModel.SetSshKeyPair(self.keyPair)
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
        # testdataUsernameDataset.cfg has upload_invalid_user_folders = False,
        # so the "INVALID_USER" folder is not included:
        self.assertEqual(sorted(usersModel.GetValuesForColname("Username")),
                         ["testuser1", "testuser2"])

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

        username = "mydata"
        privateKeyFilePath = self.keyPair.GetPrivateKeyFilePath()
        host = "127.0.0.1"
        port = 2200
        sys.stderr.write("Waiting for fake SSH server to start up...\n")
        attempts = 0
        while not OpenSSH.SshServerIsReady(username, privateKeyFilePath,
                                           host, port):
            attempts += 1
            if attempts > 10:
                raise Exception(
                    "Couldn't connect to SSH server at 127.0.0.1:2200")
            time.sleep(0.25)

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

        sys.stderr.write("Waiting for uploads to complete...\n")
        while True:
            uploadsCompleted = uploadsModel.GetCompletedCount()
            uploadsFailed = uploadsModel.GetFailedCount()
            uploadsProcessed = uploadsCompleted + uploadsFailed

            if uploadsProcessed == uploadsToBePerformed:
                break
            if uploadsProcessed > uploadsToBePerformed:
                raise Exception("Processed %s/%s uploads!"
                                % (uploadsProcessed, uploadsToBePerformed))
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
        self.fakeMyTardisPort = GetEphemeralPort()
        self.httpd = HTTPServer((self.fakeMyTardisHost, self.fakeMyTardisPort),
                                FakeMyTardisHandler)

        def FakeMyTardisServer():
            """ Run fake MyTardis server """
            self.httpd.serve_forever()
        self.fakeMyTardisServerThread = \
            threading.Thread(target=FakeMyTardisServer,
                             name="FakeMyTardisServerThread")
        self.fakeMyTardisServerThread.start()

    def StartFakeSshServer(self):
        """
        Start fake SSH server.
        """
        self.sshd = ThreadedSshServer(("127.0.0.1", 2200))

        def FakeSshServer():
            """ Run fake SSH server """
            try:
                self.sshd.serve_forever()
            except (OSError, socket.error, select.error):
                pass
        self.fakeSshServerThread = \
            threading.Thread(target=FakeSshServer,
                             name="FakeSshServerThread")
        self.fakeSshServerThread.start()


if __name__ == '__main__':
    unittest.main()

"""
Test scanning the Username / Dataset structure and uploading with SCP.
"""
import os
import sys
import time
import threading
import socket
import select

import mydata.utils.openssh as OpenSSH
from .. import MyDataTester
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.folders import FoldersModel
from ...dataviewmodels.users import UsersModel
from ...dataviewmodels.groups import GroupsModel
from ...dataviewmodels.uploads import UploadsModel
from ...dataviewmodels.verifications import VerificationsModel
from ...views.folders import FoldersView
from ...controllers.folders import FoldersController
from ...models.upload import UploadStatus
from ...utils.exceptions import PrivateKeyDoesNotExist
from ..fake_ssh_server import ThreadedSshServer


class ScanUsernameDatasetTester(MyDataTester):
    """
    Test scanning the Username / Dataset structure and uploading with SCP.
    """
    def __init__(self, *args, **kwargs):
        super(ScanUsernameDatasetTester, self).__init__(*args, **kwargs)
        self.fakeSshServerThread = None

    def setUp(self):
        super(ScanUsernameDatasetTester, self).setUp()
        super(ScanUsernameDatasetTester, self).InitializeAppAndFrame(
            'ScanUsernameDatasetTester')
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
        super(ScanUsernameDatasetTester, self).tearDown()
        self.keyPair.Delete()
        self.sshd.server_close()
        self.fakeSshServerThread.join()

    def test_scan_folders(self):
        """
        Test scanning the Username / Dataset structure and uploading with SCP.
        """
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches

        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        settingsModel.sshKeyPair = self.keyPair
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
        # testdataUsernameDataset.cfg has upload_invalid_user_folders = False,
        # so the "INVALID_USER" folder is not included:
        self.assertEqual(sorted(usersModel.GetValuesForColname("Username")),
                         ["testuser1", "testuser2"])

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).folder)
        self.assertEqual(sorted(folders), ["Birds", "Flowers"])

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).GetNumFiles()
        self.assertEqual(numFiles, 10)

        numExistingVerifiedFiles = 1
        numUnverifiedFullSizeFiles = 1
        numTriggeringMissingApiEndpoint = 1

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
        self.assertEqual(numVerificationsCompleted, numFiles)

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
        sys.stderr.write("%d/%d uploads completed.\n" % (uploadsCompleted,
                                                         uploadsProcessed))
        if uploadsFailed > 0:
            sys.stderr.write("%d/%d uploads failed.\n" % (uploadsFailed,
                                                          uploadsProcessed))

        for i in range(uploadsProcessed):
            uploadModel = uploadsModel.rowsData[i]
            if uploadModel.GetStatus() == UploadStatus.FAILED:
                sys.stderr.write(
                    "Upload failed for %s: %s\n" %
                    (uploadModel.filename, uploadModel.GetMessage().strip()))
                if uploadModel.GetTraceback():
                    sys.stderr.write(uploadModel.GetTraceback())
        sys.stderr.write("\n")

        self.assertEqual(uploadsCompleted,
                         numFiles - numExistingVerifiedFiles -
                         numUnverifiedFullSizeFiles -
                         numTriggeringMissingApiEndpoint)

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

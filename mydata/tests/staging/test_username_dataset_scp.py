"""
Test scanning the Username / Dataset structure and uploading with SCP.
"""
import sys
import time
import threading
import socket
import select

import mydata.utils.openssh as OpenSSH
import mydata.tests.fake_mytardis_helpers.get as fake_mytardis_get
from ...settings import SETTINGS
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...dataviewmodels.uploads import UploadsModel
from ...dataviewmodels.verifications import VerificationsModel
from ...controllers.folders import FoldersController
from ...models.upload import UploadStatus
from .. import MyDataScanFoldersTester
from .. import InitializeModels
from ..fake_ssh_server import ThreadedSshServer
from ..utils import GetEphemeralPort


class ScanUsernameDatasetScpTester(MyDataScanFoldersTester):
    """Test scanning the Username / Dataset structure and uploading with SCP.
    """
    def __init__(self, *args, **kwargs):
        super(ScanUsernameDatasetScpTester, self).__init__(*args, **kwargs)
        self.fakeSshServerThread = None
        self.fakeSshServerStopped = False
        self.scpPort = None

    def setUp(self):
        super(ScanUsernameDatasetScpTester, self).setUp()
        #logger.SetLevel(logging.DEBUG)
        # The fake SSH server needs to know the public
        # key so it can authenticate the test client.
        # So we need to ensure that the MyData keypair
        # is generated before starting the fake SSH server.
        self.keyPair = OpenSSH.FindOrCreateKeyPair("MyDataTest")
        self.scpPort = GetEphemeralPort()
        fake_mytardis_get.SCP_PORT = self.scpPort
        self.StartFakeSshServer()

    def tearDown(self):
        super(ScanUsernameDatasetScpTester, self).tearDown()
        if not self.fakeSshServerStopped:
            self.sshd.shutdown()
            self.fakeSshServerThread.join()
        self.keyPair.Delete()

    def test_scan_folders(self):
        """Test scanning the Username / Dataset structure and uploading with SCP.
        """
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        self.UpdateSettingsFromCfg("testdataUsernameDataset")
        self.assertEqual(SETTINGS.miscellaneous.uuid, "1234567890")
        self.assertEqual(SETTINGS.general.instrumentName, "Test Instrument")
        ValidateSettings()
        # Reset global settings' uploader model, so we when we next call
        # the SETTINGS.uploaderModel property method, we'll generate a
        # new UploaderModel instance, using the up-to-date
        # SETTINGS.general.instrumentName:
        SETTINGS.uploaderModel = None
        SETTINGS.uploaderModel.UploadUploaderInfo()
        self.assertEqual(SETTINGS.uploaderModel.name, "Test Instrument")
        SETTINGS.uploaderModel.sshKeyPair = self.keyPair
        InitializeModels()
        foldersModel = DATAVIEW_MODELS['folders']
        foldersModel.ScanFolders(MyDataScanFoldersTester.ProgressCallback)
        # testdataUsernameDataset.cfg has upload_invalid_user_folders = False,
        # so the "INVALID_USER" folder is not included:
        usersModel = DATAVIEW_MODELS['users']
        self.assertEqual(
            sorted(usersModel.GetValuesForColname("Username")),
            ["testuser1", "testuser2"])

        folders = []
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).folderName)
        self.assertEqual(sorted(folders),
                         ["Birds", "Dataset with spaces", "Flowers"])

        numFiles = 0
        for row in range(foldersModel.GetRowCount()):
            numFiles += foldersModel.GetFolderRecord(row).numFiles
        self.assertEqual(numFiles, 11)

        numExistingVerifiedFiles = 1
        numUnverifiedFullSizeFiles = 1
        numTriggeringMissingApiEndpoint = 1

        DATAVIEW_MODELS['verifications'] = VerificationsModel()
        verificationsModel = DATAVIEW_MODELS['verifications']
        DATAVIEW_MODELS['uploads'] = UploadsModel()
        uploadsModel = DATAVIEW_MODELS['uploads']
        foldersController = FoldersController(self.app.frame)
        # This helps with PostEvent's logging in mydata/events/__init__.py:
        self.app.foldersController = foldersController

        username = "mydata"
        privateKeyFilePath = self.keyPair.privateKeyFilePath
        host = "127.0.0.1"
        sys.stderr.write("Waiting for fake SSH server to start up...\n")
        attempts = 0
        while not OpenSSH.SshServerIsReady(username, privateKeyFilePath,
                                           host, self.scpPort):
            attempts += 1
            if attempts > 10:
                raise Exception(
                    "Couldn't connect to SSH server at 127.0.0.1:%s"
                    % self.scpPort)
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

        sys.stderr.write("\n")
        sys.stderr.write("%d/%d uploads completed.\n" % (uploadsCompleted,
                                                         uploadsProcessed))
        if uploadsFailed > 0:
            sys.stderr.write("%d/%d uploads failed.\n" % (uploadsFailed,
                                                          uploadsProcessed))

        for i in range(uploadsProcessed):
            uploadModel = uploadsModel.rowsData[i]
            if uploadModel.status == UploadStatus.FAILED:
                sys.stderr.write(
                    "Upload failed for %s: %s\n" %
                    (uploadModel.filename, uploadModel.message.strip()))
                if uploadModel.traceback:
                    sys.stderr.write(uploadModel.traceback)
        sys.stderr.write("\n")

        self.assertEqual(uploadsCompleted,
                         numFiles - numExistingVerifiedFiles -
                         numUnverifiedFullSizeFiles -
                         numTriggeringMissingApiEndpoint)

    def StartFakeSshServer(self):
        """
        Start fake SSH server.
        """
        self.sshd = ThreadedSshServer(("127.0.0.1", self.scpPort))

        def FakeSshServer():
            """ Run fake SSH server """
            try:
                self.sshd.serve_forever()
            except (IOError, OSError, socket.error, select.error):
                pass
        self.fakeSshServerThread = \
            threading.Thread(target=FakeSshServer, name="FakeSshServerThread")
        self.fakeSshServerThread.start()

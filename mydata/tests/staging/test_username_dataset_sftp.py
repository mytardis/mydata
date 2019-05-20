"""
Test scanning the Username / Dataset structure and uploading with SFTP.
"""
import logging
import sys
import tempfile
import time
import threading
import socket
import select

import six
import wx

import mydata.utils.openssh as OpenSSH
import mydata.tests.fake_mytardis_helpers.get as fake_mytardis_get
from ...logs import logger
from ...settings import SETTINGS
from ...models.settings.validation import ValidateSettings
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...dataviewmodels.uploads import UploadsModel
from ...dataviewmodels.verifications import VerificationsModel
from ...controllers.folders import FoldersController
from ...models.upload import UploadStatus
from ...threads.flags import FLAGS
from .. import MyDataScanFoldersTester
from .. import InitializeModels
from ..fake_sftp_server import SshServerInterface
from ..fake_sftp_server import ThreadedSftpServer
from ..utils import Subtract
from ..utils import GetEphemeralPort


class ScanUsernameDatasetSftpTester(MyDataScanFoldersTester):
    """Test scanning the Username / Dataset structure and uploading with SFTP
    """
    def __init__(self, *args, **kwargs):
        super(ScanUsernameDatasetSftpTester, self).__init__(*args, **kwargs)
        self.fakeSftpServerThread = None
        self.fakeSftpServerStopped = False
        self.scpPort = None

    def setUp(self):
        super(ScanUsernameDatasetSftpTester, self).setUp()
        # logger.SetLevel(logging.INFO)
        logging.getLogger("requests").setLevel(logging.INFO)

        # The fake SFTP server needs to know the public
        # key so it can authenticate the test client.
        # So we need to ensure that the MyData key pair
        # is generated before starting the fake SFTP server.
        with tempfile.NamedTemporaryFile() as tempConfig:
            keyPath = tempConfig.name
        self.keyPair = OpenSSH.NewKeyPair("MyDataTest", keyPath=keyPath)
        assert OpenSSH.FindKeyPair("MyDataTest", keyPath=keyPath)
        pubKeyBytes = self.keyPair.privateKey.get_base64().encode("ascii")
        if pubKeyBytes not in SshServerInterface.authorized_keys:
            SshServerInterface.authorized_keys.append(pubKeyBytes)
        self.scpPort = GetEphemeralPort()
        fake_mytardis_get.SFTP_PORT = self.scpPort
        self.StartFakeSftpServer()

    def tearDown(self):
        super(ScanUsernameDatasetSftpTester, self).tearDown()
        self.keyPair.Delete()
        if not self.fakeSftpServerStopped:
            self.sftpd.shutdown()
            self.fakeSftpServerThread.join()

    def test_scan_folders(self):
        """Test scanning the Username / Dataset structure and uploading with SFTP
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

        sys.stderr.write("Waiting for fake SFTP server to start up...\n")
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

        sys.stderr.write("Testing canceling uploads...\n")
        loggerOutput = logger.GetValue()

        def StartUploads():
            """
            Start Uploads worker
            """
            foldersController.InitForUploads()
            for row in range(foldersModel.GetRowCount()):
                folderModel = foldersModel.GetFolderRecord(row)
                foldersController.StartUploadsForFolder(folderModel)

        startUploadsThread = threading.Thread(
            target=StartUploads, name="StartUploads")
        # Do this synchronously to ensure that the completed flag is reset:
        foldersController.InitializeStatusFlags()
        startUploadsThread.start()
        sys.stderr.write("Waiting for uploads to start...\n")
        while uploadsModel.GetCount() == 0:
            time.sleep(0.01)
        while uploadsModel.rowsData[0].status == UploadStatus.NOT_STARTED:
            time.sleep(0.01)
        sys.stderr.write("Canceling uploads...\n")
        FLAGS.shouldAbort = True
        foldersController.ShutDownUploadThreads(event=wx.PyEvent())
        startUploadsThread.join()
        FLAGS.shouldAbort = False
        newLogs = Subtract(logger.GetValue(), loggerOutput)
        self.assertIn("Data scans and uploads were canceled.", newLogs)

        sys.stderr.write(
            "\nTesting with missing 'scp_username' storage box attribute...\n")
        # This UUID tells our fake MyTardis server to simulate a
        # missing storage box attribute:
        SETTINGS.miscellaneous.uuid = "1234567891"
        loggerOutput = logger.GetValue()
        foldersController.InitForUploads()
        self.assertEqual(uploadsModel.GetCompletedCount(), 0)
        self.assertTrue(foldersController.failed)
        newLogs = Subtract(logger.GetValue(), loggerOutput)
        self.assertIn(
            "Key 'scp_username' not found in attributes for storage box",
            newLogs)
        self.assertEqual(uploadsModel.GetCompletedCount(), 0)
        SETTINGS.miscellaneous.uuid = "1234567890"

        sys.stderr.write(
            "\nTesting attempted uploads with invalid file paths...\n")
        foldersController.InitForUploads()
        loggerOutput = logger.GetValue()
        for row in range(foldersModel.GetRowCount()):
            folderModel = foldersModel.GetFolderRecord(row)
            for dataFileIndex in range(folderModel.numFiles):
                folderModel.dataFilePaths['files'][dataFileIndex] += "_INVALID"
            foldersController.StartUploadsForFolder(folderModel)
        foldersController.FinishedScanningForDatasetFolders()
        newLogs = Subtract(logger.GetValue(), loggerOutput)
        six.assertRegex(
            self, newLogs, (".*Not uploading .+, because it has been "
                            "moved, renamed or deleted.*"))
        self.assertEqual(uploadsModel.GetCompletedCount(), 0)

    def StartFakeSftpServer(self):
        """
        Start fake SFTP server.
        """
        self.sftpd = ThreadedSftpServer(("127.0.0.1", self.scpPort))

        def FakeSftpServer():
            """ Run fake SFTP server """
            try:
                self.sftpd.serve_forever()
            except (IOError, OSError, socket.error, select.error):
                pass
        self.fakeSftpServerThread = \
            threading.Thread(target=FakeSftpServer, name="FakeSftpServerThread")
        self.fakeSftpServerThread.daemon = True
        self.fakeSftpServerThread.start()

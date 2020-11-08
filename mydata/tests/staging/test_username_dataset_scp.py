"""
Test scanning the Username / Dataset structure and uploading with SCP.
"""
import logging
import sys
import time
import threading
import socket
import select
import unittest

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
from ..fake_ssh_server import ThreadedSshServer
from ..utils import Subtract
from ..utils import GetEphemeralPort


@unittest.skip(
    "Not working in Python 3 yet. "
    "SFTP test worked in Python 3, but we're reverting to SCP for now.")
class ScanUsernameDatasetScpTester(MyDataScanFoldersTester):
    """
    Test scanning the Username / Dataset structure and uploading with SCP.
    """
    def __init__(self, *args, **kwargs):
        super(ScanUsernameDatasetScpTester, self).__init__(*args, **kwargs)
        self.fakeSshServerThread = None
        self.fakeSshServerStopped = False
        self.scpPort = None

    def setUp(self):
        super(ScanUsernameDatasetScpTester, self).setUp()
        logger.SetLevel(logging.DEBUG)
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
        self.keyPair.Delete()
        if not self.fakeSshServerStopped:
            self.sshd.shutdown()
            self.fakeSshServerThread.join()

    def test_scan_folders(self):
        """
        Test scanning the Username / Dataset structure and uploading with SCP.
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
        ssh = [host, self.scpPort, username, OpenSSH.NormalizeLocalPath(privateKeyFilePath)]
        while not OpenSSH.SshServerIsReady(ssh):
            attempts += 1
            if attempts > 10:
                raise Exception("Couldn't connect to SSH server at 127.0.0.1:%s" % self.scpPort)
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
        # We don't need to have an active SCP process during the Cancel for
        # the test to pass, but if we do, that will improve test coverage,
        # because UploadModel.Cancel() will need to terminate the SCP process.
        # If we wait too long to request canceling, the cancel request might
        # not be processed before the uploads are completed, hence the short
        # sleep times below.  Ideally all races conditions should be removed
        # from the "Cancel" test, but a slightly "racy" test is better then
        # not having any test!
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
            "\nTesting handling of invalid path to SCP binary...\n")
        OpenSSH.OPENSSH.scp += "_INVALID"
        loggerOutput = logger.GetValue()
        foldersController.InitForUploads()
        for row in range(foldersModel.GetRowCount()):
            folderModel = foldersModel.GetFolderRecord(row)
            foldersController.StartUploadsForFolder(folderModel)
        foldersController.FinishedScanningForDatasetFolders()
        OpenSSH.OPENSSH.scp = OpenSSH.OPENSSH.scp.rstrip("_INVALID")
        newLogs = Subtract(logger.GetValue(), loggerOutput)
        if sys.platform.startswith("win"):
            self.assertRegex(
                newLogs, (".*The system cannot find the file specified.*"))
        else:
            self.assertRegex(
                newLogs, (".*No such file or directory.*"))

        sys.stderr.write(
            "\nTesting handling of invalid path to SSH binary...\n")
        # SSH would normally be called to run "mkdir -p" on the staging server,
        # but it won't be if that has already been done in the current session
        # for the given directory, due to the OpenSSH.REMOTE_DIRS_CREATED
        # cache. We'll clear the cache here to force the remote mkdir (via ssh)
        # command to run.
        OpenSSH.REMOTE_DIRS_CREATED = dict()
        OpenSSH.OPENSSH.ssh += "_INVALID"
        loggerOutput = logger.GetValue()
        foldersController.InitForUploads()
        for row in range(foldersModel.GetRowCount()):
            folderModel = foldersModel.GetFolderRecord(row)
            foldersController.StartUploadsForFolder(folderModel)
        foldersController.FinishedScanningForDatasetFolders()
        OpenSSH.OPENSSH.ssh = OpenSSH.OPENSSH.ssh.rstrip("_INVALID")
        newLogs = Subtract(logger.GetValue(), loggerOutput)
        if sys.platform.startswith("win"):
            self.assertRegex(
                newLogs, (".*The system cannot find the file specified.*"))
        else:
            self.assertRegex(
                newLogs, (".*No such file or directory.*"))

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
        self.assertRegex(
            newLogs, (".*Not uploading .+, because it has been "
                      "moved, renamed or deleted.*"))
        self.assertEqual(uploadsModel.GetCompletedCount(), 0)

        # Now let's try to upload without a functioning SCP server:
        sys.stderr.write(
            "\nTesting attempted uploads while SCP server is offline...\n")
        self.sshd.shutdown()
        self.fakeSshServerThread.join()
        self.fakeSshServerStopped = True
        defaultTimeout = SETTINGS.miscellaneous.connectionTimeout
        SETTINGS.miscellaneous.connectionTimeout = 1
        sys.stderr.write(
            "\tSSH ConnectionTimeout: %s second(s)\n"
            % SETTINGS.miscellaneous.connectionTimeout)
        sys.stderr.write(
            "\tMax upload retries: %s\n" % SETTINGS.advanced.maxUploadRetries)
        sys.stderr.write("\tNumber of uploads: %s\n\n" % uploadsProcessed)
        foldersController.InitForUploads()
        loggerOutput = logger.GetValue()
        for row in range(foldersModel.GetRowCount()):
            folderModel = foldersModel.GetFolderRecord(row)
            for dataFileIndex in range(folderModel.numFiles):
                folderModel.dataFilePaths['files'][dataFileIndex] = \
                    folderModel.dataFilePaths['files'][dataFileIndex] \
                    .rstrip("_INVALID")
            foldersController.StartUploadsForFolder(folderModel)
        foldersController.FinishedScanningForDatasetFolders()
        newLogs = Subtract(logger.GetValue(), loggerOutput)

        for uploadModel in uploadsModel.rowsData:
            self.assertEqual(uploadModel.status, UploadStatus.FAILED)
            self.assertEqual(uploadModel.retries, 1)
            sys.stderr.write(
                "Upload failed for %s: %s\n"
                % (uploadModel.filename, uploadModel.message.strip()))
        sys.stderr.write("\n")

        self.assertRegex(
            newLogs,
            ".*ssh: connect to host localhost port %s: Connection refused.*"
            "|"
            ".*ssh: connect to host localhost port %s: Operation timed out.*"
            "|"
            ".*Connection timed out during banner exchange.*"
            % (self.scpPort, self.scpPort))
        self.assertEqual(uploadsModel.GetCompletedCount(), 0)
        SETTINGS.miscellaneous.connectionTimeout = defaultTimeout

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
        self.fakeSshServerThread.daemon = True
        self.fakeSshServerThread.start()

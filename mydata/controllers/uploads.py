"""
The main controller class for managing datafile uploads.

Most of this content used to be part of the FoldersController
class.
"""
import os
# urllib2 is not available in Python 3, but it is only used
# for poster which can be replaced by requests-toolbelt:
import urllib2
import json
import traceback
import mimetypes
import threading
from datetime import datetime

import wx

from ..utils.openssh import UploadFile

from ..settings import SETTINGS
from ..models.settings.miscellaneous import MiscellaneousSettingsModel
from ..models.upload import UploadModel
from ..models.upload import UploadStatus
from ..models.datafile import DataFileModel
from ..utils import SafeStr
from ..utils.exceptions import DoesNotExist
from ..utils.exceptions import Unauthorized
from ..utils.exceptions import InternalServerError
from ..utils.exceptions import SshException
from ..utils.exceptions import StorageBoxAttributeNotFound
from ..events import PostEvent
from ..logs import logger


class UploadMethod(object):
    """
    Enumerated data type for upload methods,
    POST to MyTardis API and SCP via staging
    """
    # pylint: disable=invalid-name
    HTTP_POST = 0
    VIA_STAGING = 1


class UploadDatafileRunnable(object):
    """
    The Run method of this class provides the functionality of
    the upload workers.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, foldersController, foldersModel, folderModel,
                 dataFileIndex, uploadsModel,
                 existingUnverifiedDatafile, verificationModel,
                 bytesUploadedPreviously=None):
        self.foldersController = foldersController
        self.foldersModel = foldersModel
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.uploadsModel = uploadsModel
        self.uploadModel = None
        self.existingUnverifiedDatafile = existingUnverifiedDatafile
        self.verificationModel = verificationModel
        self.bytesUploadedPreviously = bytesUploadedPreviously
        self.mimeTypes = mimetypes.MimeTypes()
        self.uploadsThreadingLock = threading.Lock()

    def Run(self):
        """
        Upload the file specified by the folderModel and dataFileIndex
        using foldersController.uploadMethod
        """
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        self.uploadsThreadingLock.acquire()
        uploadDataViewId = self.uploadsModel.GetMaxDataViewId() + 1
        self.uploadModel = UploadModel(dataViewId=uploadDataViewId,
                                       folderModel=self.folderModel,
                                       dataFileIndex=self.dataFileIndex)
        if self.verificationModel:
            self.uploadModel.existingUnverifiedDatafile = \
                self.verificationModel.existingUnverifiedDatafile
        self.uploadsModel.AddRow(self.uploadModel)
        self.uploadsThreadingLock.release()
        self.uploadModel.bytesUploadedPreviously = self.bytesUploadedPreviously

        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileName = os.path.basename(dataFilePath)
        dataFileDirectory = \
            self.folderModel.GetDataFileDirectory(self.dataFileIndex)

        if not os.path.exists(dataFilePath) or \
                self.folderModel.FileIsTooNewToUpload(self.dataFileIndex):
            if not os.path.exists(dataFilePath):
                message = ("Not uploading file, because it has been "
                           "moved, renamed or deleted.")
            else:
                message = ("Not uploading file, "
                           "in case it is still being modified.")
            logger.warning(message.replace('file', dataFilePath))
            self.uploadsModel.SetMessage(self.uploadModel, message)
            self.uploadsModel.SetStatus(self.uploadModel, UploadStatus.FAILED)
            PostEvent(
                self.foldersController.UploadFailedEvent(
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    uploadModel=self.uploadModel))
            return

        message = "Getting data file size..."
        self.uploadsModel.SetMessage(self.uploadModel, message)
        dataFileSize = self.folderModel.GetDataFileSize(self.dataFileIndex)
        self.uploadModel.fileSize = dataFileSize

        if self.foldersController.IsShuttingDown():
            return

        dataFileMd5Sum = None
        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST or \
                not self.existingUnverifiedDatafile:
            message = "Calculating MD5 checksum..."
            self.uploadsModel.SetMessage(self.uploadModel, message)

            if SETTINGS.miscellaneous.fakeMd5Sum:
                dataFileMd5Sum = MiscellaneousSettingsModel.GetFakeMd5Sum()
                logger.warning("Faking MD5 sum for %s" % dataFilePath)
            else:
                dataFileMd5Sum = \
                    self.folderModel.CalculateMd5Sum(
                        self.dataFileIndex,
                        progressCallback=self.Md5ProgressCallback,
                        canceledCallback=self.CanceledCallback)

            if self.uploadModel.canceled:
                self.foldersController.canceled = True
                logger.debug("Upload for \"%s\" was canceled "
                             "before it began uploading." %
                             self.uploadModel.GetRelativePathToUpload())
                return
        else:
            dataFileSize = int(self.existingUnverifiedDatafile.size)

        self.uploadModel.SetProgress(0)
        self.uploadsModel.UploadProgressUpdated(self.uploadModel)

        if self.foldersController.IsShuttingDown():
            return

        dataFileDict = None
        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST or \
                not self.existingUnverifiedDatafile:
            message = "Checking MIME type..."
            self.uploadsModel.SetMessage(self.uploadModel, message)
            dataFileMimeType = self.mimeTypes.guess_type(dataFilePath)[0]

            if self.foldersController.IsShuttingDown():
                return
            message = "Defining JSON data for POST..."
            self.uploadsModel.SetMessage(self.uploadModel, message)
            datasetUri = self.folderModel.datasetModel.resourceUri
            dataFileCreatedTime = \
                self.folderModel.GetDataFileCreatedTime(self.dataFileIndex)
            dataFileModifiedTime = \
                self.folderModel.GetDataFileModifiedTime(self.dataFileIndex)
            dataFileDict = {
                "dataset": datasetUri,
                "filename": dataFileName,
                "directory": dataFileDirectory,
                "md5sum": dataFileMd5Sum,
                "size": dataFileSize,
                "mimetype": dataFileMimeType,
                "created_time": dataFileCreatedTime,
                "modification_time": dataFileModifiedTime,
            }
            if self.uploadModel.canceled:
                self.foldersController.canceled = True
                logger.debug("Upload for \"%s\" was canceled "
                             "before it began uploading." %
                             self.uploadModel.GetRelativePathToUpload())
                return
        else:
            dataFileDict = self.existingUnverifiedDatafile.json

        message = "Uploading..."
        self.uploadsModel.SetMessage(self.uploadModel, message)
        self.uploadModel.startTime = datetime.now()

        try:
            if self.foldersController.uploadMethod == UploadMethod.HTTP_POST:
                self.UploadFileWithPost(dataFileDict)
            else:
                self.UploadFileToStaging(dataFileDict)
        except Exception as err:
            logger.error(traceback.format_exc())
            self.FinalizeUpload(uploadSuccess=False, message=SafeStr(err))
            return

    def CanceledCallback(self):
        """
        Called by MD5 calculation method to check whether uploads
        have been canceled.
        """
        return self.foldersController.IsShuttingDown() or \
            self.uploadModel.canceled

    def Md5ProgressCallback(self, bytesSummed):
        """
        Called by MD5 calculation method to update progress.
        """
        if self.uploadModel.canceled:
            self.foldersController.canceled = True
            return
        size = self.folderModel.GetDataFileSize(self.dataFileIndex)
        if size > 0:
            percentComplete = 100.0 - ((size - bytesSummed) * 100.0) / size
        else:
            percentComplete = 100
        self.uploadModel.SetProgress(int(percentComplete))
        self.uploadsModel.UploadProgressUpdated(self.uploadModel)
        if size >= (1024 * 1024 * 1024):
            message = "%3.1f %%  MD5 summed" % percentComplete
        else:
            message = "%3d %%  MD5 summed" % int(percentComplete)
        self.uploadsModel.SetMessage(self.uploadModel, message)

    def ProgressCallback(self, current, total, message=None):
        """
        Updates upload progress.
        """
        if self.uploadModel.canceled:
            self.foldersController.canceled = True
            return
        elif self.uploadModel.status == UploadStatus.COMPLETED:
            return
        if current is None:
            # For a zero-sized file, current will be None
            # before its upload, and 0 after is upload.
            percentComplete = 0
            current = 0
        elif total > 0:
            percentComplete = \
                100.0 - ((total - current) * 100.0) / total
        else:
            percentComplete = 100
        self.uploadModel.SetBytesUploaded(current)
        self.uploadModel.SetProgress(int(percentComplete))
        self.uploadsModel.UploadProgressUpdated(self.uploadModel)
        if message:
            self.uploadsModel.SetMessage(self.uploadModel, message)
        else:
            if total >= (1024 * 1024 * 1024):
                message = "%3.1f %%  uploaded" % percentComplete
            else:
                message = "%3d %%  uploaded" % int(percentComplete)
            self.uploadsModel.SetMessage(self.uploadModel, message)

    def UploadFileWithPost(self, dataFileDict):
        """
        Upload a file by POSTing to the MyTardis API's /api/v1/dataset_file/
        endpoint.  Uploading large files (> 100 MB) using this method is not
        recommended because the current version of the MyTardis API can use
        significant server memory during deserialization.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)

        def PosterCallback(param, current, total):
            """
            Callback for progress updates from POST uploads
            """
            # pylint: disable=unused-argument
            self.ProgressCallback(current, total)

        try:
            _ = DataFileModel.UploadDataFileWithPost(
                dataFilePath, dataFileDict, self.uploadsModel,
                self.uploadModel, PosterCallback)
            self.FinalizeUpload(uploadSuccess=True)
            return
        except ValueError as err:
            self.uploadModel.traceback = traceback.format_exc()
            errString = SafeStr(err)
            if errString == "read of closed file" or \
                    errString == "seek of closed file":
                logger.debug("Aborting upload for \"%s\" because "
                             "file handle was closed." %
                             self.uploadModel.GetRelativePathToUpload())
            else:
                logger.error(traceback.format_exc())
                self.FinalizeUpload(uploadSuccess=False, message=SafeStr(err))
            return
        except urllib2.HTTPError as err:
            self.uploadModel.traceback = traceback.format_exc()
            logger.error(traceback.format_exc())
            errorResponse = err.read()
            logger.error(errorResponse)
            PostEvent(self.foldersController.ShutdownUploadsEvent(failed=True))
            message = "An error occured while trying to POST data to " \
                "the MyTardis server.\n\n"
            try:
                # If running MyTardis in DEBUG mode, there should
                # be an error_message returned in JSON format.
                message += "ERROR: \"%s\"" \
                    % json.loads(errorResponse)['error_message']
            except:
                message += SafeStr(err)
            if err.code == 409:
                message += \
                    "\n\nA Duplicate Key error occurred, suggesting that " \
                    "multiple MyData instances could be trying to create " \
                    "the same DataFile records concurrently."
            PostEvent(
                self.foldersController.ShowMessageDialogEvent(
                    title="MyData", message=message, icon=wx.ICON_ERROR))

    def UploadFileToStaging(self, dataFileDict):
        """
        Upload a file to staging (Using SCP).
        """
        # pylint:disable=too-many-locals
        # pylint:disable=too-many-branches
        sshKeyPair = SETTINGS.uploaderModel.sshKeyPair
        dataFileDict['uploader_uuid'] = SETTINGS.miscellaneous.uuid
        dataFileDict['requester_key_fingerprint'] = sshKeyPair.fingerprint
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileSize = self.folderModel.GetDataFileSize(self.dataFileIndex)
        response = None
        if not self.existingUnverifiedDatafile:
            response = \
                DataFileModel.CreateDataFileForStagingUpload(dataFileDict)
            if response.status_code != 201:
                dataFileName = os.path.basename(dataFilePath)
                folderName = self.folderModel.folderName
                myTardisUsername = SETTINGS.general.username
                UploadDatafileRunnable.HandleFailedCreateDataFile(
                    response, dataFileName, folderName, myTardisUsername)
                return
        uploadToStagingRequest = SETTINGS.uploaderModel.uploadToStagingRequest
        try:
            host = uploadToStagingRequest.scpHostname
            port = uploadToStagingRequest.scpPort
            location = uploadToStagingRequest.location
            username = uploadToStagingRequest.scpUsername
        except StorageBoxAttributeNotFound as err:
            self.uploadModel.traceback = traceback.format_exc()
            PostEvent(
                self.foldersController.ShutdownUploadsEvent(
                    failed=True))
            message = SafeStr(err)
            logger.error(message)
            PostEvent(
                self.foldersController.ShowMessageDialogEvent(
                    title="MyData", message=message, icon=wx.ICON_ERROR))
            return
        privateKeyFilePath = sshKeyPair.privateKeyFilePath
        if self.existingUnverifiedDatafile:
            uri = self.existingUnverifiedDatafile.replicas[0].uri
            remoteFilePath = "%s/%s" % (location.rstrip('/'), uri)
        else:
            # DataFile creation via the MyTardis API doesn't
            # return JSON, but if a DataFile record is created
            # without specifying a storage location, then a
            # temporary location is returned for the client
            # to copy/upload the file to.
            tempUrl = response.text
            remoteFilePath = tempUrl
            dataFileId = response.headers['Location'].split('/')[-2]
            self.uploadModel.dataFileId = dataFileId
        while True:
            # Upload retries loop:
            try:
                UploadFile(dataFilePath,
                           dataFileSize,
                           username,
                           privateKeyFilePath,
                           host, port, remoteFilePath,
                           self.ProgressCallback,
                           self.foldersController,
                           self.uploadModel)
                # Break out of upload retries loop.
                break
            except SshException as err:
                # includes the ScpException subclass
                if self.foldersController.IsShuttingDown() or \
                        self.uploadModel.canceled:
                    return
                self.uploadModel.traceback = traceback.format_exc()
                if self.uploadModel.retries < \
                        SETTINGS.advanced.maxUploadRetries:
                    logger.warning(SafeStr(err))
                    self.uploadModel.retries += 1
                    logger.debug("Restarting upload for " + dataFilePath)
                    self.uploadModel.SetProgress(0)
                    continue
                else:
                    logger.error(traceback.format_exc())
                    self.FinalizeUpload(
                        uploadSuccess=False, message=SafeStr(err))
                    return
        if self.uploadModel.canceled:
            logger.debug("FoldersController: "
                         "Aborting upload for \"%s\"."
                         % self.uploadModel
                         .GetRelativePathToUpload())
            return
        # If an exception occurs (e.g. can't connect to SCP server)
        # while uploading a zero-byte file, don't want to mark it
        # as completed, just because zero bytes have been uploaded.
        if self.uploadModel.bytesUploaded == dataFileSize and \
                self.uploadModel.status != UploadStatus.CANCELED and \
                self.uploadModel.status != UploadStatus.FAILED:
            uploadSuccess = True
            if self.existingUnverifiedDatafile:
                datafileId = \
                    self.existingUnverifiedDatafile.datafileId
            else:
                location = response.headers['location']
                datafileId = location.split("/")[-2]
            verificationDelay = SETTINGS.miscellaneous.verificationDelay

            def RequestVerification():
                """
                Request verification via MyTardis API

                POST-uploaded files are verified automatically by MyTardis, but
                for staged files, we need to request verification after
                uploading to staging.
                """
                DataFileModel.Verify(datafileId)
            if wx.PyApp.IsMainLoopRunning() and \
                    int(verificationDelay) > 0:
                timer = threading.Timer(verificationDelay,
                                        RequestVerification)
                timer.start()
                self.uploadModel.verificationTimer = timer
            else:
                # Don't use a timer if we are running
                # unit tests:
                RequestVerification()
        else:
            uploadSuccess = False
        self.FinalizeUpload(uploadSuccess)
        return

    @staticmethod
    def HandleFailedCreateDataFile(response, dataFileName, folderName,
                                   myTardisUsername):
        """
        Handle DataFile creation exceptions for staging upload method.
        """
        if response.status_code == 401:
            message = "Couldn't create datafile \"%s\" " \
                      "for folder \"%s\"." % (dataFileName, folderName)
            message += "\n\n"
            message += \
                "Please ask your MyTardis administrator to " \
                "check the permissions of the \"%s\" user " \
                "account." % myTardisUsername
            raise Unauthorized(message)
        elif response.status_code == 404:
            message = "Encountered a 404 (Not Found) error " \
                "while attempting to create a datafile " \
                "record for \"%s\" in folder \"%s\"." \
                      % (dataFileName, folderName)
            message += "\n\n"
            message += \
                "Please ask your MyTardis administrator to " \
                "check whether an appropriate staging " \
                "storage box exists."
            raise DoesNotExist(message)
        elif response.status_code == 500:
            message = "Couldn't create datafile \"%s\" " \
                      "for folder \"%s\"." \
                      % (dataFileName, folderName)
            message += "\n\n"
            message += "An Internal Server Error occurred."
            message += "\n\n"
            message += \
                "If running MyTardis in DEBUG mode, " \
                "more information may be available below. " \
                "Otherwise, please ask your MyTardis " \
                "administrator to check in their logs " \
                "for more information."
            message += "\n\n"
            try:
                message += "ERROR: \"%s\"" \
                    % response.json()['error_message']
            except:
                message = "Internal Server Error: " \
                    "See MyData's log for further " \
                    "information."
            finally:
                raise InternalServerError(message)

    def FinalizeUpload(self, uploadSuccess, message=None):
        """
        Finalize upload
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileSize = self.folderModel.GetDataFileSize(self.dataFileIndex)
        dataFileName = os.path.basename(dataFilePath)
        uploadMethod = self.foldersController.uploadMethod
        if uploadSuccess:
            logger.debug("Upload succeeded for %s" % dataFileName)
            self.uploadsModel.SetStatus(
                self.uploadModel, UploadStatus.COMPLETED)
            if not message:
                message = "Upload complete!"
            self.uploadsModel.SetMessage(self.uploadModel, message)
            self.uploadModel.SetLatestTime(datetime.now())
            self.uploadModel.SetProgress(100)
        else:
            self.uploadsModel.SetStatus(self.uploadModel, UploadStatus.FAILED)
            if not message:
                if uploadMethod == UploadMethod.VIA_STAGING and \
                        self.uploadModel.bytesUploaded < dataFileSize:
                    message = "Only %s of %s bytes were uploaded for %s" \
                        % (self.uploadModel.bytesUploaded, dataFileSize,
                           dataFilePath)
                else:
                    message = "Upload failed for %s" % dataFileName
            logger.error(message)
            self.uploadsModel.SetMessage(self.uploadModel, message)
            self.uploadModel.SetProgress(0)
        self.uploadsModel.UploadProgressUpdated(self.uploadModel)
        self.folderModel.SetDataFileUploaded(
            self.dataFileIndex, uploaded=uploadSuccess)
        self.foldersModel.FolderStatusUpdated(self.folderModel)
        event = self.foldersController.UploadCompleteEvent(
            folderModel=self.folderModel,
            dataFileIndex=self.dataFileIndex,
            uploadModel=self.uploadModel)
        PostEvent(event)
        if uploadMethod == UploadMethod.HTTP_POST:
            try:
                self.uploadModel.bufferedReader.close()
            except:
                logger.error(traceback.format_exc())

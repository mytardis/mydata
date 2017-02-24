"""
The main controller class for managing datafile uploads.

Most of this content used to be part of the FoldersController
class.
"""

# pylint: disable=missing-docstring

import os
try:
    import urllib2
except ImportError:
    # urllib2 is not available in Python 3
    # But it is only used for poster,
    # which can be replaced by requests-toolbelt
    pass
import json
import traceback
import mimetypes
import threading
from datetime import datetime

import wx

from mydata.utils.openssh import UploadFile

from mydata.models.settings.miscellaneous import MiscellaneousSettingsModel
from mydata.models.upload import UploadModel
from mydata.models.upload import UploadStatus
from mydata.models.datafile import DataFileModel
from mydata.utils import SafeStr
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import Unauthorized
from mydata.utils.exceptions import InternalServerError
from mydata.utils.exceptions import SshException
from mydata.utils.exceptions import StorageBoxAttributeNotFound
from mydata.events import PostEvent
from mydata.logs import logger


class UploadMethod(object):
    # pylint: disable=invalid-name
    HTTP_POST = 0
    VIA_STAGING = 1


class UploadDatafileRunnable(object):
    # pylint: disable=too-many-instance-attributes
    def __init__(self, foldersController, foldersModel, folderModel,
                 dataFileIndex, uploadsModel, settingsModel,
                 existingUnverifiedDatafile, verificationModel,
                 bytesUploadedPreviously=None):
        self.foldersController = foldersController
        self.foldersModel = foldersModel
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.uploadsModel = uploadsModel
        self.uploadModel = None
        self.settingsModel = settingsModel
        self.existingUnverifiedDatafile = existingUnverifiedDatafile
        self.verificationModel = verificationModel
        self.bytesUploadedPreviously = bytesUploadedPreviously
        self.mimeTypes = mimetypes.MimeTypes()
        self.uploadsThreadingLock = threading.Lock()

    def GetDatafileIndex(self):
        return self.dataFileIndex

    def GetDatafilePath(self):
        return self.folderModel.GetDataFilePath(self.dataFileIndex)

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
        self.uploadModel.SetExistingUnverifiedDatafile(
            self.verificationModel.GetExistingUnverifiedDatafile())
        self.uploadsModel.AddRow(self.uploadModel)
        self.uploadsThreadingLock.release()
        self.uploadModel.SetBytesUploadedPreviously(
            self.bytesUploadedPreviously)

        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileName = os.path.basename(dataFilePath)
        dataFileDirectory = \
            self.folderModel.GetDataFileDirectory(self.dataFileIndex)

        if self.folderModel.FileIsTooNewToUpload(self.dataFileIndex):
            message = "Not uploading file, in case it is still being modified."
            logger.warning(message.replace('file', dataFilePath))
            self.uploadsModel.SetMessage(self.uploadModel, message)
            self.uploadsModel.SetStatus(self.uploadModel, UploadStatus.FAILED)
            PostEvent(
                self.foldersController.UploadCompleteEvent(
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    uploadModel=self.uploadModel))
            return

        message = "Getting data file size..."
        self.uploadsModel.SetMessage(self.uploadModel, message)
        dataFileSize = self.folderModel.GetDataFileSize(self.dataFileIndex)
        self.uploadModel.SetFileSize(dataFileSize)

        if self.foldersController.IsShuttingDown():
            return

        dataFileMd5Sum = None
        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST or \
                not self.existingUnverifiedDatafile:
            message = "Calculating MD5 checksum..."
            self.uploadsModel.SetMessage(self.uploadModel, message)

            if self.settingsModel.miscellaneous.fakeMd5Sum:
                dataFileMd5Sum = MiscellaneousSettingsModel.GetFakeMd5Sum()
                logger.warning("Faking MD5 sum for %s" % dataFilePath)
            else:
                dataFileMd5Sum = \
                    self.folderModel.CalculateMd5Sum(
                        self.dataFileIndex,
                        progressCallback=self.Md5ProgressCallback,
                        canceledCallback=self.CanceledCallback)

            if self.uploadModel.Canceled():
                self.foldersController.SetCanceled()
                logger.debug("Upload for \"%s\" was canceled "
                             "before it began uploading." %
                             self.uploadModel.GetRelativePathToUpload())
                return
        else:
            dataFileSize = int(self.existingUnverifiedDatafile.GetSize())

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
            datasetUri = self.folderModel.GetDatasetModel().GetResourceUri()
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
            if self.uploadModel.Canceled():
                self.foldersController.SetCanceled()
                logger.debug("Upload for \"%s\" was canceled "
                             "before it began uploading." %
                             self.uploadModel.GetRelativePathToUpload())
                return
        else:
            dataFileDict = self.existingUnverifiedDatafile.GetJson()

        message = "Uploading..."
        self.uploadsModel.SetMessage(self.uploadModel, message)
        self.uploadModel.SetStartTime(datetime.now())

        try:
            if self.foldersController.uploadMethod == UploadMethod.HTTP_POST:
                self.UploadFileWithPost(dataFileDict)
            else:
                self.UploadFileToStaging(dataFileDict)
        except Exception as err:
            self.uploadsModel.SetMessage(self.uploadModel, SafeStr(err))
            self.uploadsModel.SetStatus(self.uploadModel, UploadStatus.FAILED)
            self.uploadModel.SetTraceback(traceback.format_exc())
            if dataFileDirectory != "":
                logger.error("Upload failed for datafile " + dataFileName +
                             " in subdirectory " + dataFileDirectory +
                             " of folder " + self.folderModel.GetFolder())
            else:
                logger.error("Upload failed for datafile " + dataFileName +
                             " in folder " + self.folderModel.GetFolder())
            logger.error(traceback.format_exc())

    def CanceledCallback(self):
        """
        Called by MD5 calculation method to check whether uploads
        have been canceled.
        """
        return self.foldersController.IsShuttingDown() or \
            self.uploadModel.Canceled()

    def Md5ProgressCallback(self, bytesProcessed):
        """
        Called by MD5 calculation method to update progress.
        """
        if self.uploadModel.Canceled():
            self.foldersController.SetCanceled()
            return
        dataFileSize = self.folderModel.GetDataFileSize(self.dataFileIndex)
        if dataFileSize > 0:
            percentComplete = \
                100.0 - ((dataFileSize - bytesProcessed) * 100.0) \
                / dataFileSize
        else:
            percentComplete = 100
        self.uploadModel.SetProgress(int(percentComplete))
        self.uploadsModel.UploadProgressUpdated(self.uploadModel)
        if dataFileSize >= (1024 * 1024 * 1024):
            message = "%3.1f %%  MD5 summed" % percentComplete
        else:
            message = "%3d %%  MD5 summed" % int(percentComplete)
        self.uploadsModel.SetMessage(self.uploadModel, message)

    def ProgressCallback(self, current, total, message=None):
        """
        Updates upload progress.
        """
        if self.uploadModel.Canceled():
            self.foldersController.SetCanceled()
            return
        elif self.uploadModel.GetStatus() == UploadStatus.COMPLETED:
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
            # pylint: disable=unused-argument
            self.ProgressCallback(current, total)

        try:
            response = DataFileModel.UploadDataFileWithPost(
                self.settingsModel, dataFilePath, dataFileDict,
                self.uploadsModel, self.uploadModel, PosterCallback)
            self.FinalizeUpload(response, postSuccess=True, uploadSuccess=True)
        except ValueError as err:
            self.uploadModel.SetTraceback(
                traceback.format_exc())
            errString = SafeStr(err)
            if errString == "read of closed file" or \
                    errString == "seek of closed file":
                logger.debug("Aborting upload for \"%s\" because "
                             "file handle was closed." %
                             self.uploadModel.GetRelativePathToUpload())
                return
            else:
                raise
        except urllib2.HTTPError as err:
            self.uploadModel.SetTraceback(
                traceback.format_exc())
            logger.error(traceback.format_exc())
            errorResponse = err.read()
            logger.error(errorResponse)
            PostEvent(
                self.foldersController.ShutdownUploadsEvent(
                    failed=True))
            message = "An error occured while trying to POST data to " \
                "the MyTardis server.\n\n"
            try:
                # If running MyTardis in DEBUG mode, there should
                # be an error_message returned in JSON format.
                message += "ERROR: \"%s\"" \
                    % json.loads(errorResponse)['error_message']
            except:
                message += SafeStr(err)
            PostEvent(
                self.foldersController
                .ShowMessageDialogEvent(title="MyData",
                                        message=message,
                                        icon=wx.ICON_ERROR))

    def UploadFileToStaging(self, dataFileDict):
        """
        Upload a file to staging (Using SCP).
        """
        # pylint:disable=too-many-locals
        # pylint:disable=too-many-branches
        # pylint:disable=too-many-return-statements
        dataFileDict['uploader_uuid'] = self.settingsModel.miscellaneous.uuid
        dataFileDict['requester_key_fingerprint'] = \
            self.settingsModel.sshKeyPair.GetFingerprint()
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileSize = self.folderModel.GetDataFileSize(self.dataFileIndex)
        postSuccess = False
        response = None
        if not self.existingUnverifiedDatafile:
            response = DataFileModel.CreateDataFileForStagingUpload(
                self.settingsModel, dataFileDict)
            postSuccess = (response.status_code == 201)
            logger.debug(response.text)
            if not postSuccess:
                dataFileName = os.path.basename(dataFilePath)
                folderName = self.folderModel.GetFolder()
                myTardisUsername = self.settingsModel.general.username
                UploadDatafileRunnable.HandleFailedCreateDataFile(
                    response, dataFileName, folderName, myTardisUsername)
                return
        uploadToStagingRequest = self.settingsModel.uploadToStagingRequest
        host = uploadToStagingRequest.GetScpHostname()
        port = uploadToStagingRequest.GetScpPort()
        location = uploadToStagingRequest.GetLocation()
        username = uploadToStagingRequest.GetScpUsername()
        privateKeyFilePath = \
            self.settingsModel.sshKeyPair.GetPrivateKeyFilePath()
        if self.existingUnverifiedDatafile:
            uri = self.existingUnverifiedDatafile\
                .GetReplicas()[0].GetUri()
            remoteFilePath = "%s/%s" % (location.rstrip('/'),
                                        uri)
        else:
            # DataFile creation via the MyTardis API doesn't
            # return JSON, but if a DataFile record is created
            # without specifying a storage location, then a
            # temporary location is returned for the client
            # to copy/upload the file to.
            tempUrl = response.text
            remoteFilePath = tempUrl
            dataFileId = \
                response.headers['Location'].split('/')[-2]
            self.uploadModel.SetDataFileId(dataFileId)
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
            except IOError as err:
                if self.foldersController.IsShuttingDown() or \
                        self.uploadModel.Canceled():
                    return
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                if self.uploadModel.GetRetries() < \
                        self.settingsModel.advanced.maxUploadRetries:
                    logger.warning(SafeStr(err))
                    self.uploadModel.IncrementRetries()
                    logger.debug("Restarting upload for " +
                                 dataFilePath)
                    self.uploadModel.SetProgress(0)
                    continue
                else:
                    raise
            except DoesNotExist as err:
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                # This generally means that MyTardis's API couldn't assign
                # a staging storage box, possibly because the MyTardis
                # administrator hasn't created a storage box record with
                # the correct storage box attribute, i.e.
                # (key="type", value="receiving"). The staging storage box
                # should also have a storage box option with
                # (key="location", value="/mnt/.../MYTARDIS_STAGING")
                PostEvent(
                    self.foldersController.ShutdownUploadsEvent(
                        failed=True))
                message = SafeStr(err)
                PostEvent(
                    self.foldersController
                    .ShowMessageDialogEvent(title="MyData",
                                            message=message,
                                            icon=wx.ICON_ERROR))
                return
            except StorageBoxAttributeNotFound as err:
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                PostEvent(
                    self.foldersController.ShutdownUploadsEvent(
                        failed=True))
                message = SafeStr(err)
                PostEvent(
                    self.foldersController
                    .ShowMessageDialogEvent(title="MyData",
                                            message=message,
                                            icon=wx.ICON_ERROR))
                return
            except SshException as err:
                if self.foldersController.IsShuttingDown() or \
                        self.uploadModel.Canceled():
                    return
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                if self.uploadModel.GetRetries() < \
                        self.settingsModel.advanced.maxUploadRetries:
                    logger.warning(SafeStr(err))
                    self.uploadModel.IncrementRetries()
                    logger.debug("Restarting upload for " +
                                 dataFilePath)
                    self.uploadModel.SetProgress(0)
                    continue
                else:
                    raise
        if self.uploadModel.Canceled():
            logger.debug("FoldersController: "
                         "Aborting upload for \"%s\"."
                         % self.uploadModel
                         .GetRelativePathToUpload())
            return
        bytesUploaded = self.uploadModel.GetBytesUploaded()
        if bytesUploaded == dataFileSize:
            uploadSuccess = True
            if self.existingUnverifiedDatafile:
                datafileId = \
                    self.existingUnverifiedDatafile.GetId()
            else:
                location = response.headers['location']
                datafileId = location.split("/")[-2]
            verificationDelay = \
                self.settingsModel.miscellaneous.verificationDelay

            def RequestVerification():
                DataFileModel.Verify(self.settingsModel,
                                     datafileId)
            if wx.PyApp.IsMainLoopRunning() and \
                    int(verificationDelay) > 0:
                timer = threading.Timer(verificationDelay,
                                        RequestVerification)
                timer.start()
                self.uploadModel.SetVerificationTimer(timer)
            else:
                # Don't use a timer if we are running
                # unit tests:
                RequestVerification()

            self.FinalizeUpload(response, postSuccess, uploadSuccess)
            return
        else:
            raise Exception("Only %d of %d bytes were uploaded for %s"
                            % (bytesUploaded, dataFileSize, dataFilePath))

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

    def FinalizeUpload(self, response, postSuccess, uploadSuccess):
        """
        Finalize upload
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileName = os.path.basename(dataFilePath)
        if uploadSuccess:
            logger.debug("Upload succeeded for %s" % dataFileName)
            self.uploadsModel.SetStatus(self.uploadModel,
                                        UploadStatus.COMPLETED)
            message = "Upload complete!"
            self.uploadsModel.SetMessage(self.uploadModel, message)
            self.uploadModel.SetLatestTime(datetime.now())
            self.uploadModel.SetProgress(100)
            self.uploadsModel.UploadProgressUpdated(self.uploadModel)
            self.folderModel.SetDataFileUploaded(self.dataFileIndex,
                                                 uploaded=True)
            self.foldersModel.FolderStatusUpdated(self.folderModel)
            event = self.foldersController.UploadCompleteEvent(
                folderModel=self.folderModel,
                dataFileIndex=self.dataFileIndex,
                uploadModel=self.uploadModel)
            PostEvent(event)
        else:
            if self.foldersController.IsShuttingDown() or \
                    self.uploadModel.Canceled():
                return
            logger.error("Upload failed for " + dataFileName)
            self.uploadsModel.SetStatus(self.uploadModel, UploadStatus.FAILED)
            if not postSuccess and response is not None:
                message = "Internal Server Error: " \
                    "See MyData's log for further " \
                    "information."
                logger.error(message)
                message = response.text
            else:
                message = "Upload failed."
            self.uploadsModel.SetMessage(self.uploadModel, message)

            # self.uploadModel.SetProgress(0.0)
            self.uploadModel.SetProgress(0)
            self.uploadsModel.UploadProgressUpdated(self.uploadModel)
            self.folderModel.SetDataFileUploaded(self.dataFileIndex,
                                                 uploaded=False)
            self.foldersModel.FolderStatusUpdated(self.folderModel)
            event = self.foldersController.UploadCompleteEvent(
                folderModel=self.folderModel,
                dataFileIndex=self.dataFileIndex,
                uploadModel=self.uploadModel)
            PostEvent(event)
        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST:
            try:
                self.uploadModel.GetBufferedReader().close()
            except:
                logger.error(traceback.format_exc())

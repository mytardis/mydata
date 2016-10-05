"""
The main controller class for managing datafile uploads.

Most of this content used to be part of the FoldersController
class.
"""

# pylint: disable=missing-docstring

import os
import urllib2
import json
import io
import traceback
import mimetypes
import time
import hashlib

import poster
import requests

import wx

from mydata.utils.openssh import UploadFile

from mydata.models.upload import UploadModel
from mydata.models.upload import UploadStatus
from mydata.models.datafile import DataFileModel
from mydata.utils import ConnectionStatus
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import Unauthorized
from mydata.utils.exceptions import InternalServerError
from mydata.utils.exceptions import StagingHostRefusedSshConnection
from mydata.utils.exceptions import StagingHostSshPermissionDenied
from mydata.utils.exceptions import SshException
from mydata.utils.exceptions import ScpException
from mydata.utils.exceptions import IncompatibleMyTardisVersion
from mydata.utils.exceptions import StorageBoxAttributeNotFound
from mydata.utils.exceptions import SshControlMasterLimit

from mydata.logs import logger


class UploadMethod(object):
    # pylint: disable=invalid-name
    # pylint: disable=too-few-public-methods
    HTTP_POST = 0
    VIA_STAGING = 1


class UploadDatafileRunnable(object):
    # pylint: disable=too-many-instance-attributes
    def __init__(self, foldersController, foldersModel, folderModel,
                 dataFileIndex, uploadsModel, settingsModel,
                 existingUnverifiedDatafile, verificationModel,
                 bytesUploadedPreviously=0):
        # pylint: disable=too-many-arguments
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

    def GetDatafileIndex(self):
        return self.dataFileIndex

    def GetDatafilePath(self):
        return self.folderModel.GetDataFilePath(self.dataFileIndex)

    def Run(self):
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-return-statements
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements

        self.foldersController.uploadsThreadingLock.acquire()
        uploadDataViewId = self.uploadsModel.GetMaxDataViewId() + 1
        self.uploadModel = UploadModel(dataViewId=uploadDataViewId,
                                       folderModel=self.folderModel,
                                       dataFileIndex=self.dataFileIndex)
        self.uploadsModel.AddRow(self.uploadModel)
        self.foldersController.uploadsThreadingLock.release()
        self.uploadModel.SetBytesUploadedToStaging(
            self.bytesUploadedPreviously)

        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileName = os.path.basename(dataFilePath)
        dataFileDirectory = \
            self.folderModel.GetDataFileDirectory(self.dataFileIndex)

        ignoreNewFiles = self.settingsModel.IgnoreNewFiles()
        ignoreNewFilesMinutes = self.settingsModel.GetIgnoreNewFilesMinutes()
        ignoreNewFilesSeconds = 0
        if ignoreNewFiles:
            ignoreNewFilesSeconds = ignoreNewFilesMinutes * 60
        if (time.time() - os.path.getmtime(dataFilePath)) <= \
                ignoreNewFilesSeconds:
            message = "Not uploading file, in case it is still being modified."
            logger.warning(message.replace('file', dataFilePath))
            self.uploadsModel.SetMessage(self.uploadModel, message)
            self.uploadsModel.SetStatus(self.uploadModel, UploadStatus.FAILED)
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.uploadCompleteEvent(
                    id=self.foldersController.EVT_UPLOAD_FAILED,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    uploadModel=self.uploadModel))
            return

        logger.debug("Uploading " +
                     self.folderModel.GetDataFileName(self.dataFileIndex) +
                     "...")

        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST or \
                not self.existingUnverifiedDatafile:
            myTardisUrl = self.settingsModel.GetMyTardisUrl()
            myTardisUsername = self.settingsModel.GetUsername()
            myTardisApiKey = self.settingsModel.GetApiKey()
            if self.foldersController.uploadMethod == \
                    UploadMethod.VIA_STAGING:
                url = myTardisUrl + "/api/v1/mydata_dataset_file/"
            else:
                url = myTardisUrl + "/api/v1/dataset_file/"
            headers = {
                "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                                   myTardisApiKey)}

        if self.foldersController.IsShuttingDown():
            return

        message = "Getting data file size..."
        self.uploadsModel.SetMessage(self.uploadModel, message)
        dataFileSize = self.folderModel.GetDataFileSize(self.dataFileIndex)
        self.uploadModel.SetFileSize(dataFileSize)

        if self.foldersController.IsShuttingDown():
            return

        # The HTTP POST upload method doesn't support resuming uploads,
        # so we always (re-)create the JSON to be POSTed when we find
        # a file whose datafile record is unverified.

        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST or \
                not self.existingUnverifiedDatafile:
            message = "Calculating MD5 checksum..."
            self.uploadsModel.SetMessage(self.uploadModel, message)

            def Md5ProgressCallback(bytesProcessed):
                if self.uploadModel.Canceled():
                    self.foldersController.SetCanceled()
                    return
                percentComplete = \
                    100.0 - ((dataFileSize - bytesProcessed) * 100.0) \
                    / dataFileSize

                # self.uploadModel.SetProgress(float(percentComplete))
                self.uploadModel.SetProgress(int(percentComplete))
                self.uploadsModel.UploadProgressUpdated(self.uploadModel)
                if dataFileSize >= (1024 * 1024 * 1024):
                    message = "%3.1f %%  MD5 summed" % percentComplete
                else:
                    message = "%3d %%  MD5 summed" % int(percentComplete)
                self.uploadsModel.SetMessage(self.uploadModel, message)
                myTardisUrl = self.settingsModel.GetMyTardisUrl()
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.connectionStatusEvent(
                        myTardisUrl=myTardisUrl,
                        connectionStatus=ConnectionStatus.CONNECTED))
            dataFileMd5Sum = \
                self.CalculateMd5Sum(dataFilePath, dataFileSize,
                                     self.uploadModel,
                                     progressCallback=Md5ProgressCallback)

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
            dataFileJson = {
                "dataset": datasetUri,
                "filename": dataFileName,
                "directory": dataFileDirectory,
                "md5sum": dataFileMd5Sum,
                "size": dataFileSize,
                "mimetype": dataFileMimeType,
                "created_time": dataFileCreatedTime,
                "modification_time": dataFileModifiedTime,
            }
            if self.foldersController.uploadMethod == \
                    UploadMethod.VIA_STAGING:
                dataFileJson['uploader_uuid'] = self.settingsModel.GetUuid()
                dataFileJson['requester_key_fingerprint'] = \
                    self.settingsModel.GetSshKeyPair().GetFingerprint()

            if self.uploadModel.Canceled():
                self.foldersController.SetCanceled()
                logger.debug("Upload for \"%s\" was canceled "
                             "before it began uploading." %
                             self.uploadModel.GetRelativePathToUpload())
                return
        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST:
            message = "Initializing buffered reader..."
            self.uploadsModel.SetMessage(self.uploadModel, message)
            datafileBufferedReader = io.open(dataFilePath, 'rb')
            self.uploadModel.SetBufferedReader(datafileBufferedReader)

        def ProgressCallback(current, total, message=None):
            if self.uploadModel.Canceled():
                self.foldersController.SetCanceled()
                return
            percentComplete = \
                100.0 - ((total - current) * 100.0) / total
            self.uploadModel.SetBytesUploaded(current)
            # self.uploadModel.SetProgress(float(percentComplete))
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
            myTardisUrl = self.settingsModel.GetMyTardisUrl()
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.connectionStatusEvent(
                    myTardisUrl=myTardisUrl,
                    connectionStatus=ConnectionStatus.CONNECTED))

        # The database interactions below should go in a model class.

        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST:
            def PosterCallback(param, current, total):
                # pylint: disable=unused-argument
                ProgressCallback(current, total)

            datagen, headers = poster.encode.multipart_encode(
                {"json_data": json.dumps(dataFileJson),
                 "attached_file": datafileBufferedReader},
                cb=PosterCallback)
            opener = poster.streaminghttp.register_openers()
            opener.addheaders = [("Authorization", "ApiKey " +
                                  myTardisUsername +
                                  ":" + myTardisApiKey),
                                 ("Content-Type", "application/json"),
                                 ("Accept", "application/json")]
        elif not self.existingUnverifiedDatafile:
            headers = {
                "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                                   myTardisApiKey),
                "Content-Type": "application/json",
                "Accept": "application/json"}
            data = json.dumps(dataFileJson)

        message = "Uploading..."
        self.uploadsModel.SetMessage(self.uploadModel, message)
        postSuccess = False
        uploadSuccess = False

        request = None
        response = None
        # pylint: disable=broad-except
        # pylint: disable=too-many-nested-blocks
        try:
            if self.foldersController.uploadMethod == UploadMethod.HTTP_POST:
                request = urllib2.Request(url, datagen, headers)
            try:
                if self.foldersController.uploadMethod == \
                        UploadMethod.HTTP_POST:
                    response = urllib2.urlopen(request)
                    postSuccess = True
                    uploadSuccess = True
                else:
                    if not self.existingUnverifiedDatafile:
                        response = requests.post(headers=headers, url=url,
                                                 data=data)
                        postSuccess = response.status_code >= 200 and \
                            response.status_code < 300
                        logger.debug(response.text)
                    if postSuccess or self.existingUnverifiedDatafile:
                        uploadToStagingRequest = self.settingsModel\
                            .GetUploadToStagingRequest()
                        host = uploadToStagingRequest.GetScpHostname()
                        port = uploadToStagingRequest.GetScpPort()
                        location = uploadToStagingRequest.GetLocation()
                        username = uploadToStagingRequest.GetScpUsername()
                        privateKeyFilePath = self.settingsModel\
                            .GetSshKeyPair().GetPrivateKeyFilePath()
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
                        while True:
                            try:
                                UploadFile(dataFilePath,
                                           dataFileSize,
                                           username,
                                           privateKeyFilePath,
                                           host, port, remoteFilePath,
                                           ProgressCallback,
                                           self.foldersController,
                                           self.uploadModel)
                            except IOError, err:
                                self.uploadModel.SetTraceback(
                                    traceback.format_exc())
                                if self.uploadModel.GetRetries() < \
                                        self.settingsModel.GetMaxUploadRetries():
                                    logger.warning(str(err))
                                    self.uploadModel.IncrementRetries()
                                    logger.debug("Restarting upload for " +
                                                 dataFilePath)
                                    message = "This file will be re-uploaded..."
                                    self.uploadsModel.SetMessage(
                                        self.uploadModel, message)
                                    self.uploadModel.SetProgress(0)
                                    continue
                                else:
                                    raise
                            except ScpException, err:
                                self.uploadModel.SetTraceback(
                                    traceback.format_exc())
                                if self.uploadModel.GetRetries() < \
                                        self.settingsModel.GetMaxUploadRetries():
                                    logger.warning(str(err))
                                    self.uploadModel.IncrementRetries()
                                    logger.debug("Restarting upload for " +
                                                 dataFilePath)
                                    message = \
                                        "This file will be re-uploaded..."
                                    self.uploadsModel.SetMessage(
                                        self.uploadModel, message)
                                    self.uploadModel.SetProgress(0)
                                    continue
                                else:
                                    raise
                            except SshException, err:
                                self.uploadModel.SetTraceback(
                                    traceback.format_exc())
                                if self.uploadModel.GetRetries() < \
                                        self.settingsModel.GetMaxUploadRetries():
                                    logger.warning(str(err))
                                    self.uploadModel.IncrementRetries()
                                    logger.debug("Restarting upload for " +
                                                 dataFilePath)
                                    message = \
                                        "This file will be re-uploaded..."
                                    self.uploadsModel.SetMessage(
                                        self.uploadModel, message)
                                    self.uploadModel.SetProgress(0)
                                    continue
                                else:
                                    raise
                            break
                        if self.uploadModel.Canceled():
                            logger.debug("FoldersController: "
                                         "Aborting upload for \"%s\"."
                                         % self.uploadModel
                                         .GetRelativePathToUpload())
                            return
                        bytesUploaded = 0
                        bytesUploaded = self.uploadModel.GetBytesUploaded()
                        if bytesUploaded == dataFileSize:
                            uploadSuccess = True
                            if self.existingUnverifiedDatafile:
                                datafileId = \
                                    self.existingUnverifiedDatafile.GetId()
                            else:
                                location = response.headers['location']
                                datafileId = location.split("/")[-2]
                            DataFileModel.Verify(self.settingsModel,
                                                 datafileId)
                        else:
                            raise Exception(
                                "Only %d of %d bytes were uploaded for %s"
                                % (bytesUploaded, dataFileSize, dataFilePath))
                    if not postSuccess and not self.existingUnverifiedDatafile:
                        if response.status_code == 401:
                            message = "Couldn't create datafile \"%s\" " \
                                      "for folder \"%s\"." \
                                      % (dataFileName,
                                         self.folderModel.GetFolder())
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
                                      % (dataFileName,
                                         self.folderModel.GetFolder())
                            message += "\n\n"
                            message += \
                                "Please ask your MyTardis administrator to " \
                                "check whether an appropriate staging " \
                                "storage box exists."
                            raise DoesNotExist(message)
                        elif response.status_code == 500:
                            message = "Couldn't create datafile \"%s\" " \
                                      "for folder \"%s\"." \
                                      % (dataFileName,
                                         self.folderModel.GetFolder())
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
                            # pylint: disable=bare-except
                            try:
                                message += "ERROR: \"%s\"" \
                                    % response.json()['error_message']
                            except:
                                message = "Internal Server Error: " \
                                    "See MyData's log for further " \
                                    "information."
                            raise InternalServerError(message)
                        else:
                            # If POST fails for some other reason,
                            # for now, we will just populate the upload's
                            # message field with an error message, and
                            # allow the other uploads to continue.  There
                            # may be other critical errors where we should
                            # raise an exception and abort all uploads.
                            pass
            except DoesNotExist, err:
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                # This generally means that MyTardis's API couldn't assign
                # a staging storage box, possibly because the MyTardis
                # administrator hasn't created a storage box record with
                # the correct storage box attribute, i.e.
                # (key="Staging", value=True). The staging storage box should
                # also have a storage box option with
                # (key="location", value="/mnt/.../MYTARDIS_STAGING")
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.shutdownUploadsEvent(
                        failed=True))
                message = str(err)
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController
                    .showMessageDialogEvent(title="MyData",
                                            message=message,
                                            icon=wx.ICON_ERROR))
                return
            except StagingHostRefusedSshConnection, err:
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.shutdownUploadsEvent(
                        failed=True))
                message = str(err)
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController
                    .showMessageDialogEvent(title="MyData",
                                            message=message,
                                            icon=wx.ICON_ERROR))
                return
            except StagingHostSshPermissionDenied, err:
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.shutdownUploadsEvent(
                        failed=True))
                message = str(err)
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController
                    .showMessageDialogEvent(title="MyData",
                                            message=message,
                                            icon=wx.ICON_ERROR))
                return
            except SshControlMasterLimit, err:
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.shutdownUploadsEvent(
                        failed=True))
                message = str(err)
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController
                    .showMessageDialogEvent(title="MyData",
                                            message=message,
                                            icon=wx.ICON_ERROR))
                return
            except ScpException, err:
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                if self.foldersController.IsShuttingDown() or \
                        self.uploadModel.Canceled():
                    return
                message = str(err)
                message += "\n\n" + err.command
                logger.error(message)
            except ValueError, err:
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                if str(err) == "read of closed file" or \
                        str(err) == "seek of closed file":
                    logger.debug("Aborting upload for \"%s\" because "
                                 "file handle was closed." %
                                 self.uploadModel.GetRelativePathToUpload())
                    return
                else:
                    raise
            except IncompatibleMyTardisVersion, err:
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.shutdownUploadsEvent(
                        failed=True))
                message = str(err)
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController
                    .showMessageDialogEvent(title="MyData",
                                            message=message,
                                            icon=wx.ICON_ERROR))
                return
            except StorageBoxAttributeNotFound, err:
                self.uploadModel.SetTraceback(
                    traceback.format_exc())
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.shutdownUploadsEvent(
                        failed=True))
                message = str(err)
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController
                    .showMessageDialogEvent(title="MyData",
                                            message=message,
                                            icon=wx.ICON_ERROR))
                return
        except urllib2.HTTPError, err:
            self.uploadModel.SetTraceback(
                traceback.format_exc())
            logger.error("url: " + url)
            logger.error(traceback.format_exc())
            errorResponse = err.read()
            logger.error(errorResponse)
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.shutdownUploadsEvent(
                    failed=True))
            message = "An error occured while trying to POST data to " \
                "the MyTardis server.\n\n"
            # pylint: disable=bare-except
            try:
                # If running MyTardis in DEBUG mode, there should
                # be an error_message returned in JSON format.
                message += "ERROR: \"%s\"" \
                    % json.loads(errorResponse)['error_message']
            except:
                message += str(err)
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController
                .showMessageDialogEvent(title="MyData",
                                        message=message,
                                        icon=wx.ICON_ERROR))
            return
        except Exception, err:
            self.uploadsModel.SetMessage(self.uploadModel, str(err))
            self.uploadsModel.SetStatus(self.uploadModel, UploadStatus.FAILED)
            self.uploadModel.SetTraceback(traceback.format_exc())
            if not self.foldersController.IsShuttingDown():
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.connectionStatusEvent(
                        myTardisUrl=self.settingsModel.GetMyTardisUrl(),
                        connectionStatus=ConnectionStatus.DISCONNECTED))
            if dataFileDirectory != "":
                logger.error("Upload failed for datafile " + dataFileName +
                             " in subdirectory " + dataFileDirectory +
                             " of folder " + self.folderModel.GetFolder())
            else:
                logger.error("Upload failed for datafile " + dataFileName +
                             " in folder " + self.folderModel.GetFolder())
            if not self.existingUnverifiedDatafile:
                logger.debug(url)
                if hasattr(err, "code"):
                    logger.error(err.code)
                logger.error(str(err))
                if self.foldersController.uploadMethod == \
                        UploadMethod.HTTP_POST:
                    if request is not None:
                        logger.error(str(request.header_items()))
                    else:
                        logger.error("request is None.")
                if response is not None:
                    if self.foldersController.uploadMethod == \
                            UploadMethod.HTTP_POST:
                        logger.debug(response.read())
                    else:
                        # logger.debug(response.text)
                        pass
                else:
                    logger.error("response is None.")
                if hasattr(err, "headers"):
                    logger.debug(str(err.headers))
                if hasattr(response, "headers"):
                    # logger.debug(str(response.headers))
                    pass
            logger.error(traceback.format_exc())
            return

        if uploadSuccess:
            logger.debug("Upload succeeded for " + dataFilePath)
            self.uploadsModel.SetStatus(self.uploadModel,
                                        UploadStatus.COMPLETED)
            message = "Upload complete!"
            self.uploadsModel.SetMessage(self.uploadModel, message)
            self.uploadModel.SetProgress(100)
            self.uploadsModel.UploadProgressUpdated(self.uploadModel)
            self.folderModel.SetDataFileUploaded(self.dataFileIndex,
                                                 uploaded=True)
            self.foldersModel.FolderStatusUpdated(self.folderModel)
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.uploadCompleteEvent(
                    id=self.foldersController.EVT_UPLOAD_COMPLETE,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    uploadModel=self.uploadModel))
        else:
            if self.foldersController.IsShuttingDown() or \
                    self.uploadModel.Canceled():
                return
            logger.error("Upload failed for " + dataFilePath)
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
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.uploadCompleteEvent(
                    id=self.foldersController.EVT_UPLOAD_COMPLETE,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    uploadModel=self.uploadModel))
        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST:
            # pylint: disable=bare-except
            try:
                self.uploadModel.GetBufferedReader().close()
            except:
                logger.error(traceback.format_exc())

    def CalculateMd5Sum(self, filePath, fileSize, uploadModel,
                        progressCallback=None):
        """
        Calculate MD5 checksum.
        """
        md5 = hashlib.md5()

        defaultChunkSize = 128 * 1024
        maxChunkSize = 16 * 1024 * 1024
        chunkSize = defaultChunkSize
        while (fileSize / chunkSize) > 50 and chunkSize < maxChunkSize:
            chunkSize = chunkSize * 2
        bytesProcessed = 0
        with open(filePath, 'rb') as fileHandle:
            # Note that the iter() func needs an empty byte string
            # for the returned iterator to halt at EOF, since read()
            # returns b'' (not just '').
            for chunk in iter(lambda: fileHandle.read(chunkSize), b''):
                if self.foldersController.IsShuttingDown() or \
                        uploadModel.Canceled():
                    logger.debug("Aborting MD5 calculation for "
                                 "%s" % filePath)
                    return None
                md5.update(chunk)
                bytesProcessed += len(chunk)
                del chunk
                if progressCallback:
                    progressCallback(bytesProcessed)
        return md5.hexdigest()

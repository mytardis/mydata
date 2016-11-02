"""
The main controller class for managing datafile verifications.

class VerifyDatafileRunnable(object):
  Run:
    HandleNonExistentDataFile:
      Post EVT_DIDNT_FIND_FILE_ON_SERVER  # DataFile record doesn't exist
    HandleExistingDatafile:
      HandleExistingVerifiedDatafile:
        Post EVT_FOUND_VERIFIED_DATAFILE  # Verified DFO exists!
      HandleExistingUnverifiedDatafile:
        HandleResumableUpload:
          HandleUnverifiedNotFoundOnStaging:
            Post EVT_UNVERIFIED_NOT_FOUND_ON_STAGING
          HandleFullSizeResumableUpload:
            Post EVT_FOUND_UNVERIFIED_BUT_FULL_SIZE_DATAFILE
          HandleIncompleteResumableUpload:
            Post EVT_INCOMPLETE_FILE_ON_STAGING
        HandleUnresumableUpload:
          Either: Post EVT_FOUND_UNVERIFIED_BUT_FULL_SIZE_DATAFILE
              or: Post EVT_FOUND_UNVERIFIED_NO_DFOS
"""

import os
import threading
import traceback

import wx

from mydata.models.replica import ReplicaModel

from mydata.models.verification import VerificationModel
from mydata.models.verification import VerificationStatus
from mydata.models.datafile import DataFileModel
from mydata.controllers.uploads import UploadMethod
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import FileNotFoundOnStaging
from mydata.utils.exceptions import MissingMyDataReplicaApiEndpoint
from mydata.utils.openssh import OldCountBytesUploadedToStaging
from mydata.utils.exceptions import StagingHostRefusedSshConnection
from mydata.utils.exceptions import StagingHostSshPermissionDenied
from mydata.utils.exceptions import IncompatibleMyTardisVersion
from mydata.utils.exceptions import StorageBoxAttributeNotFound

from mydata.logs import logger


class VerifyDatafileRunnable(object):
    """
    The Run method of this class provides the functionality of
    the verification workers.  Data files found locally are
    looked up on the MyTardis server, and are classified according
    to whether they are found on the server, whether they are
    verified, and if not, whether they have been completely or
    partially uploaded.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, foldersController, foldersModel, folderModel,
                 dataFileIndex, settingsModel, testRun=False):
        # pylint: disable=too-many-arguments
        self.foldersController = foldersController
        self.foldersModel = foldersModel
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.settingsModel = settingsModel
        self.verificationsModel = foldersController.verificationsModel
        self.verificationModel = None
        self.testRun = testRun

    def GetDatafileIndex(self):
        """
        Return the DataFile index within the folderModel.
        """
        return self.dataFileIndex

    def GetDatafilePath(self):
        """
        Return the path to the DataFile.
        """
        return self.folderModel.GetDataFilePath(self.dataFileIndex)

    def GetDatafileSize(self):
        """
        Return the size of the DataFile.
        """
        return self.folderModel.GetDataFileSize(self.dataFileIndex)

    def Run(self):
        """
        This method provides the functionality of
        the verification workers.  Data files found locally are
        looked up on the MyTardis server, and are classified according
        to whether they are found on the server, whether they are
        verified, and if not, whether they have been completely or
        partially uploaded.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileDirectory = \
            self.folderModel.GetDataFileDirectory(self.dataFileIndex)
        dataFileName = os.path.basename(dataFilePath)
        fc = self.foldersController  # pylint: disable=invalid-name
        if not hasattr(fc, "verificationsThreadingLock"):
            fc.verificationsThreadingLock = threading.Lock()
        fc.verificationsThreadingLock.acquire()
        verificationDataViewId = self.verificationsModel.GetMaxDataViewId() + 1
        self.verificationModel = \
            VerificationModel(dataViewId=verificationDataViewId,
                              folderModel=self.folderModel,
                              dataFileIndex=self.dataFileIndex)
        self.verificationsModel.AddRow(self.verificationModel)
        fc.verificationsThreadingLock.release()
        self.verificationModel.SetMessage("Looking for matching file on "
                                          "MyTardis server...")
        self.verificationModel.SetStatus(VerificationStatus.IN_PROGRESS)
        self.verificationsModel.MessageUpdated(self.verificationModel)

        try:
            dataset = self.folderModel.GetDatasetModel()
            if not dataset:  # test runs don't create required datasets
                raise DoesNotExist("Dataset doesn't exist.")
            existingDatafile = DataFileModel.GetDataFile(
                settingsModel=self.settingsModel,
                dataset=dataset,
                filename=dataFileName,
                directory=dataFileDirectory)
            self.verificationModel.SetMessage("Found datafile on "
                                              "MyTardis server.")
            self.verificationModel.SetStatus(VerificationStatus.FOUND_VERIFIED)
            self.verificationsModel.MessageUpdated(self.verificationModel)
            self.HandleExistingDatafile(existingDatafile)
        except DoesNotExist:
            self.HandleNonExistentDataFile()
        except:  # pylint: disable=bare-except
            logger.error(traceback.format_exc())

    def HandleNonExistentDataFile(self):
        """
        If file doesn't exist on the server, it needs to be uploaded.
        """
        self.verificationModel.SetMessage("Didn't find datafile on "
                                          "MyTardis server.")
        self.verificationModel.SetStatus(VerificationStatus.NOT_FOUND)
        self.verificationsModel.MessageUpdated(self.verificationModel)
        self.verificationsModel.SetComplete(self.verificationModel)
        wx.PostEvent(
            self.foldersController.notifyWindow,
            self.foldersController.didntFindDatafileOnServerEvent(
                id=self.foldersController.EVT_DIDNT_FIND_FILE_ON_SERVER,
                foldersController=self.foldersController,
                folderModel=self.folderModel,
                dataFileIndex=self.dataFileIndex,
                verificationModel=self.verificationModel))

    def HandleExistingDatafile(self, existingDatafile):
        """
        Check if existing DataFile is verified.
        """
        replicas = existingDatafile.GetReplicas()
        if len(replicas) == 0 or not replicas[0].IsVerified():
            self.HandleExistingUnverifiedDatafile(existingDatafile)
        else:
            self.HandleExistingVerifiedDatafile()

    def HandleExistingUnverifiedDatafile(self, existingDatafile):
        """
        If the existing unverified DataFile was uploaded via POST, we just
        need to wait for it to be verified.  But if it was uploaded via
        staging, we might be able to resume a partial upload.
        """
        self.verificationModel.SetExistingUnverifiedDatafile(existingDatafile)
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        replicas = existingDatafile.GetReplicas()
        message = "Found datafile record for %s " \
            "but it has no verified replicas." % dataFilePath
        logger.debug(message)
        message = "Found unverified datafile record on MyTardis."
        self.verificationModel.SetMessage(message)
        uploadToStagingRequest = self.settingsModel.GetUploadToStagingRequest()
        if self.foldersController.uploadMethod == \
                UploadMethod.VIA_STAGING and \
                uploadToStagingRequest is not None and \
                uploadToStagingRequest.IsApproved() and \
                len(replicas) > 0:
            # Can resume partial uploads:
            self.HandleResumableUpload(existingDatafile)
        else:
            # Can't resume partial uploads:
            self.HandleUnresumableUpload(existingDatafile)

    def HandleResumableUpload(self, existingDatafile):
        """
        Determine whether part of the file is already available
        on staging.
        """
        replicas = existingDatafile.GetReplicas()
        bytesUploadedPreviously = None
        try:
            bytesUploadedPreviously = \
                ReplicaModel.CountBytesUploadedToStaging(
                    self.settingsModel, replicas[0].GetId())
            logger.debug("%s bytes uploaded to staging for %s"
                         % (bytesUploadedPreviously,
                            replicas[0].GetUri()))
        except FileNotFoundOnStaging, err:
            self.HandleUnverifiedNotFoundOnStaging(existingDatafile)
            return
        except MissingMyDataReplicaApiEndpoint:
            # /api/v1/mydata_replica/ is not available on this MyTardis server.
            # mytardis-app-mydata needs updating on the server.
            # For now, assume the unverified file is full size on staging.
            # The old method of running "wc -c " remotely over ssh was
            # inefficient.
            try:
                uploadToStagingRequest = \
                    self.settingsModel.GetUploadToStagingRequest()
                username = uploadToStagingRequest.GetScpUsername()
            except IncompatibleMyTardisVersion, err:
                self.verificationsModel.SetComplete(self.verificationModel)
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
                self.verificationsModel.SetComplete(self.verificationModel)
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

            privateKeyFilePath = self.settingsModel\
                .GetSshKeyPair().GetPrivateKeyFilePath()
            host = uploadToStagingRequest.GetScpHostname()
            port = uploadToStagingRequest.GetScpPort()
            location = uploadToStagingRequest.GetLocation()
            remoteFilePath = "%s/%s" % (location.rstrip('/'),
                                        replicas[0].GetUri())
            try:
                bytesUploadedPreviously = \
                    OldCountBytesUploadedToStaging(
                        remoteFilePath,
                        username, privateKeyFilePath, host, port,
                        self.settingsModel)
            except FileNotFoundOnStaging, err:
                self.HandleUnverifiedNotFoundOnStaging(existingDatafile)
                return
            except StagingHostRefusedSshConnection, err:
                self.verificationsModel.SetComplete(self.verificationModel)
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
                self.verificationsModel.SetComplete(self.verificationModel)
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

        if bytesUploadedPreviously == long(existingDatafile.GetSize()):
            self.HandleFullSizeResumableUpload(existingDatafile)
        else:
            self.HandleIncompleteResumableUpload(
                existingDatafile,
                bytesUploadedPreviously)

    def HandleFullSizeResumableUpload(self, existingDatafile):
        """
        If the existing unverified DataFile upload is the correct size
        in staging, then we can request its verification, but no upload
        is needed.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        self.verificationModel\
            .SetMessage("Found unverified full-size datafile "
                        "on staging server.")
        self.verificationModel.SetStatus(
            VerificationStatus.FOUND_UNVERIFIED_FULL_SIZE)
        self.verificationsModel.MessageUpdated(self.verificationModel)
        self.folderModel.SetDataFileUploaded(self.dataFileIndex, True)
        self.foldersModel.FolderStatusUpdated(self.folderModel)
        if existingDatafile and not self.testRun:
            if existingDatafile.GetMd5Sum() == \
                    self.settingsModel.GetFakeMd5Sum():
                logger.warning("MD5(%s): %s" %
                               (dataFilePath, existingDatafile.GetMd5Sum()))
            else:
                DataFileModel.Verify(self.settingsModel, existingDatafile.GetId())
        self.verificationsModel.SetComplete(self.verificationModel)
        wx.PostEvent(
            self.foldersController.notifyWindow,
            self.foldersController
            .foundUnverifiedDatafileEvent(
                id=self.foldersController
                .EVT_FOUND_UNVERIFIED_BUT_FULL_SIZE_DATAFILE,
                folderModel=self.folderModel,
                dataFileIndex=self.dataFileIndex,
                dataFilePath=dataFilePath))
        if self.testRun:
            message = "FOUND UNVERIFIED UPLOAD FOR: %s" \
                % self.folderModel.GetDataFileRelPath(self.dataFileIndex)
            logger.testrun(message)

    def HandleIncompleteResumableUpload(self, existingDatafile,
                                        bytesUploadedPreviously):
        """
        Resume partial upload.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        self.verificationModel\
            .SetMessage("Found partially uploaded datafile "
                        "on staging server.")
        self.verificationModel\
            .SetStatus(VerificationStatus
                       .FOUND_UNVERIFIED_NOT_FULL_SIZE)
        self.verificationsModel.MessageUpdated(self.verificationModel)
        logger.debug("Re-uploading \"%s\" to staging, because "
                     "the file size is %s bytes in staging, "
                     "but it should be %s bytes."
                     % (dataFilePath,
                        bytesUploadedPreviously,
                        existingDatafile.GetSize()))
        self.verificationsModel.SetComplete(self.verificationModel)
        wx.PostEvent(
            self.foldersController.notifyWindow,
            self.foldersController.unverifiedDatafileOnServerEvent(
                id=self.foldersController.EVT_INCOMPLETE_FILE_ON_STAGING,
                foldersController=self.foldersController,
                folderModel=self.folderModel,
                dataFileIndex=self.dataFileIndex,
                existingUnverifiedDatafile=existingDatafile,
                bytesUploadedPreviously=bytesUploadedPreviously,
                verificationModel=self.verificationModel))

    def HandleUnverifiedNotFoundOnStaging(self, existingDatafile):
        """
        File has a DataFile record, and a DataFileObject record,
        marked as unverified.  The file is not accessible on staging.
        So we need to upload the entire file and create any subdirectories
        required for it on staging.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        self.verificationModel\
            .SetMessage("Unverified and not found on staging server.")
        self.verificationModel.SetStatus(
            VerificationStatus.NOT_FOUND_ON_STAGING)
        self.verificationsModel.MessageUpdated(self.verificationModel)
        logger.debug("Uploading \"%s\" to staging, because "
                     "it was not there. It does have a DataFileObject."
                     % dataFilePath)
        self.verificationsModel.SetComplete(self.verificationModel)
        wx.PostEvent(
            self.foldersController.notifyWindow,
            self.foldersController.unverifiedDatafileOnServerEvent(
                id=self.foldersController.EVT_UNVERIFIED_NOT_FOUND_ON_STAGING,
                foldersController=self.foldersController,
                folderModel=self.folderModel,
                dataFileIndex=self.dataFileIndex,
                existingUnverifiedDatafile=existingDatafile,
                bytesUploadedPreviously=None,
                verificationModel=self.verificationModel))

    def HandleUnresumableUpload(self, existingDatafile):
        """
        We found an unverified datafile on the server for which
        there is no point in checking for a resumable partial
        upload.

        This is usually because we are uploading using the POST upload method.
        Or we could be using the STAGING method but failed to find any
        DataFileObjects on the server for the datafile.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        logger.debug("Found unverified datafile record for \"%s\" "
                     "on MyTardis." % dataFilePath)
        self.verificationModel.SetMessage("Found unverified datafile record.")
        self.folderModel.SetDataFileUploaded(self.dataFileIndex, True)
        self.foldersModel.FolderStatusUpdated(self.folderModel)
        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST:
            self.verificationModel.SetStatus(
                VerificationStatus.FOUND_UNVERIFIED_FULL_SIZE)
            eventId = self.foldersController\
                .EVT_FOUND_UNVERIFIED_BUT_FULL_SIZE_DATAFILE
        else:
            self.verificationModel.SetStatus(
                VerificationStatus.FOUND_UNVERIFIED_NO_DFOS)
            eventId = self.foldersController\
                .EVT_FOUND_UNVERIFIED_NO_DFOS
        self.verificationsModel.MessageUpdated(self.verificationModel)
        if existingDatafile and not self.testRun:
            if existingDatafile.GetMd5Sum() == \
                    self.settingsModel.GetFakeMd5Sum():
                logger.warning("MD5(%s): %s" %
                               (dataFilePath, existingDatafile.GetMd5Sum()))
            else:
                DataFileModel.Verify(self.settingsModel, existingDatafile.GetId())
        self.verificationsModel.SetComplete(self.verificationModel)
        wx.PostEvent(
            self.foldersController.notifyWindow,
            self.foldersController
            .foundUnverifiedDatafileEvent(
                id=eventId,
                folderModel=self.folderModel,
                dataFileIndex=self.dataFileIndex,
                dataFilePath=dataFilePath))
        if self.testRun:
            message = "FOUND UNVERIFIED UPLOAD FOR: %s" \
                % self.folderModel.GetDataFileRelPath(self.dataFileIndex)
            logger.testrun(message)

    def HandleExistingVerifiedDatafile(self):
        """
        Found existing verified file on server.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        self.folderModel.SetDataFileUploaded(self.dataFileIndex, True)
        self.foldersModel.FolderStatusUpdated(self.folderModel)
        self.verificationsModel.SetComplete(self.verificationModel)
        wx.PostEvent(
            self.foldersController.notifyWindow,
            self.foldersController.foundVerifiedDatafileEvent(
                id=self.foldersController.EVT_FOUND_VERIFIED_DATAFILE,
                folderModel=self.folderModel,
                dataFileIndex=self.dataFileIndex,
                dataFilePath=dataFilePath))
        if self.testRun:
            message = "FOUND VERIFIED UPLOAD FOR: %s" \
                % self.folderModel.GetDataFileRelPath(self.dataFileIndex)
            logger.testrun(message)

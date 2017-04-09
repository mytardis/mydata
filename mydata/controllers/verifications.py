"""
The main controller class for managing datafile verifications.

class VerifyDatafileRunnable(object):
  Run:
    HandleNonExistentDataFile:
      Post DidntFindDatafileOnServerEvent  # DataFile record doesn't exist
    HandleExistingDatafile:
      HandleExistingVerifiedDatafile:
        Post FoundVerifiedDatafileEvent  # Verified DFO exists!
      HandleExistingUnverifiedDatafile:
        HandleUnverifiedFileOnStaging:  # Reupload if staged copy is incomplete
          HandleFullSizeStagedUpload:
            Post FoundFullSizeStagedEvent
          HandleIncompleteStagedUpload:
            Post FoundIncompleteStagedEvent
        HandleUnverifiedUnstagedUpload:  # No staged file to check size of
          Post FoundUnverifiedUnstagedEvent
"""
import os
import threading
import traceback

import wx

from ..settings import SETTINGS
from ..models.settings.miscellaneous import MiscellaneousSettingsModel
from ..models.replica import ReplicaModel
from ..models.verification import VerificationModel
from ..models.verification import VerificationStatus
from ..models.datafile import DataFileModel
from ..utils.exceptions import DoesNotExist
from ..utils.exceptions import MissingMyDataReplicaApiEndpoint
from ..events import PostEvent
from ..logs import logger
from .uploads import UploadMethod


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
                 dataFileIndex, testRun=False):
        self.foldersController = foldersController
        self.foldersModel = foldersModel
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.verificationsModel = foldersController.verificationsModel
        self.verificationModel = None
        self.testRun = testRun

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
        try:
            verificationDataViewId = \
                self.verificationsModel.GetMaxDataViewId() + 1
            self.verificationModel = \
                VerificationModel(dataViewId=verificationDataViewId,
                                  folderModel=self.folderModel,
                                  dataFileIndex=self.dataFileIndex)
            self.verificationsModel.AddRow(self.verificationModel)
        finally:
            fc.verificationsThreadingLock.release()
        self.verificationModel.message = \
            "Looking for matching file on MyTardis server..."
        self.verificationModel.status = VerificationStatus.IN_PROGRESS
        self.verificationsModel.MessageUpdated(self.verificationModel)

        try:
            dataset = self.folderModel.datasetModel
            if not dataset:  # test runs don't create required datasets
                raise DoesNotExist("Dataset doesn't exist.")
            cacheKey = \
                "%s,%s" % (dataset.datasetId, dataFilePath.encode('utf8'))
            if cacheKey in SETTINGS.verifiedDatafilesCache:
                self.verificationModel.message = \
                    "Found datafile in verified-files cache."
                self.verificationModel.status = \
                    VerificationStatus.FOUND_VERIFIED
                self.verificationsModel.MessageUpdated(self.verificationModel)
                self.HandleExistingVerifiedDatafile()
                return
            existingDatafile = DataFileModel.GetDataFile(
                dataset=dataset, filename=dataFileName,
                directory=dataFileDirectory)
            self.verificationModel.message = \
                "Found datafile on MyTardis server."
            self.verificationModel.status = VerificationStatus.FOUND_VERIFIED
            self.verificationsModel.MessageUpdated(self.verificationModel)
            self.HandleExistingDatafile(existingDatafile)
        except DoesNotExist:
            self.HandleNonExistentDataFile()
        except:
            logger.error(traceback.format_exc())

    def HandleNonExistentDataFile(self):
        """
        If file doesn't exist on the server, it needs to be uploaded.
        """
        self.verificationModel.message = \
            "Didn't find datafile on MyTardis server."
        self.verificationModel.status = VerificationStatus.NOT_FOUND
        self.verificationsModel.MessageUpdated(self.verificationModel)
        self.verificationsModel.SetComplete(self.verificationModel)
        event = self.foldersController.DidntFindDatafileOnServerEvent(
            foldersController=self.foldersController,
            folderModel=self.folderModel,
            dataFileIndex=self.dataFileIndex,
            verificationModel=self.verificationModel)
        PostEvent(event)

    def HandleExistingDatafile(self, existingDatafile):
        """
        Check if existing DataFile is verified.
        """
        if len(existingDatafile.replicas) == 0 or \
                not existingDatafile.replicas[0].verified:
            self.HandleExistingUnverifiedDatafile(existingDatafile)
        else:
            self.HandleExistingVerifiedDatafile()

    def HandleExistingUnverifiedDatafile(self, existingDatafile):
        """
        If the existing unverified DataFile was uploaded via POST, we just
        need to wait for it to be verified.  But if it was uploaded via
        staging, we might be able to resume a partial upload.
        """
        self.verificationModel.existingUnverifiedDatafile = existingDatafile
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        message = "Found datafile record for %s " \
            "but it has no verified replicas." % dataFilePath
        logger.debug(message)
        self.verificationModel.message = \
            "Found unverified datafile record on MyTardis."
        uploadToStagingRequest = SETTINGS.uploadToStagingRequest

        if self.foldersController.uploadMethod == \
                UploadMethod.VIA_STAGING and \
                uploadToStagingRequest is not None and \
                uploadToStagingRequest.approved and \
                len(existingDatafile.replicas) > 0:
            self.HandleUnverifiedFileOnStaging(existingDatafile)
        else:
            self.HandleUnverifiedUnstagedUpload(existingDatafile)

    def HandleUnverifiedFileOnStaging(self, existingDatafile):
        """
        Determine whether part of the file is already available on staging.

        The name of this method comes from MyData v0.6.x and earlier which
        uploaded files in chunks, so it could resume partial uploads by
        counting chunks in partial uploads.  Chunking has been removed in
        v0.7.0.  This method is now used when we are using the STAGING
        upload method and we found an existing DataFileObject, so resuming
        means checking if the previous upload can be found on the staging
        server and whether it is the correct size.

        MyData uses the /api/v1/mydata_replica/ API endpoint
        on the MyTardis server, which is provided by the
        mytardis-app-mydata app.
        """
        try:
            bytesUploadedPreviously = ReplicaModel.CountBytesUploadedToStaging(
                existingDatafile.replicas[0].dfoId)
            logger.debug("%s bytes uploaded to staging for %s"
                         % (bytesUploadedPreviously,
                            existingDatafile.replicas[0].uri))
        except MissingMyDataReplicaApiEndpoint:
            message = (
                "Please ask your MyTardis administrator to "
                "upgrade the mytardis-app-mydata app to include "
                "the /api/v1/mydata_replica/ API endpoint.")
            PostEvent(self.foldersController.ShowMessageDialogEvent(
                title="MyData", message=message, icon=wx.ICON_ERROR))
            return
        if bytesUploadedPreviously == int(existingDatafile.size):
            self.HandleFullSizeStagedUpload(existingDatafile)
        else:
            self.HandleIncompleteStagedUpload(
                existingDatafile, bytesUploadedPreviously)

    def HandleFullSizeStagedUpload(self, existingDatafile):
        """
        If the existing unverified DataFile upload is the correct size
        in staging, then we can request its verification, but no upload
        is needed.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        self.verificationModel.message = \
            "Found unverified full-size datafile on staging server."
        self.verificationModel.status = \
            VerificationStatus.FOUND_UNVERIFIED_FULL_SIZE
        self.verificationsModel.MessageUpdated(self.verificationModel)
        self.folderModel.SetDataFileUploaded(self.dataFileIndex, True)
        self.foldersModel.FolderStatusUpdated(self.folderModel)
        if existingDatafile and not self.testRun:
            if existingDatafile.md5sum == \
                    MiscellaneousSettingsModel.GetFakeMd5Sum():
                logger.warning("MD5(%s): %s" %
                               (dataFilePath, existingDatafile.md5sum))
            else:
                DataFileModel.Verify(existingDatafile.datafileId)
        self.verificationsModel.SetComplete(self.verificationModel)
        PostEvent(self.foldersController.FoundFullSizeStagedEvent(
            folderModel=self.folderModel, dataFileIndex=self.dataFileIndex,
            dataFilePath=dataFilePath))
        if self.testRun:
            message = "FOUND UNVERIFIED UPLOAD FOR: %s" \
                % self.folderModel.GetDataFileRelPath(self.dataFileIndex)
            logger.testrun(message)

    def HandleIncompleteStagedUpload(self, existingDatafile,
                                     bytesUploadedPreviously):
        """
        Re-upload file (resuming partial uploads is not supported).
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        self.verificationModel.message = \
            "Found partially uploaded datafile on staging server."
        self.verificationModel.status = \
            VerificationStatus.FOUND_UNVERIFIED_NOT_FULL_SIZE
        self.verificationsModel.MessageUpdated(self.verificationModel)
        logger.debug("Re-uploading \"%s\" to staging, because "
                     "the file size is %s bytes in staging, "
                     "but it should be %s bytes."
                     % (dataFilePath, bytesUploadedPreviously,
                        existingDatafile.size))
        self.verificationsModel.SetComplete(self.verificationModel)
        PostEvent(self.foldersController.FoundIncompleteStagedEvent(
            foldersController=self.foldersController,
            folderModel=self.folderModel, dataFileIndex=self.dataFileIndex,
            existingUnverifiedDatafile=existingDatafile,
            bytesUploadedPreviously=bytesUploadedPreviously,
            verificationModel=self.verificationModel))

    def HandleUnverifiedUnstagedUpload(self, existingDatafile):
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
        self.verificationModel.message = "Found unverified datafile record."
        self.folderModel.SetDataFileUploaded(self.dataFileIndex, True)
        self.foldersModel.FolderStatusUpdated(self.folderModel)
        self.verificationModel.status = \
            VerificationStatus.FOUND_UNVERIFIED_UNSTAGED
        self.verificationsModel.MessageUpdated(self.verificationModel)
        if existingDatafile and not self.testRun:
            if existingDatafile.md5sum == \
                    MiscellaneousSettingsModel.GetFakeMd5Sum():
                logger.warning("MD5(%s): %s" %
                               (dataFilePath, existingDatafile.md5sum))
            else:
                DataFileModel.Verify(existingDatafile.datafileId)
        self.verificationsModel.SetComplete(self.verificationModel)
        PostEvent(self.foldersController.FoundUnverifiedUnstagedEvent(
            folderModel=self.folderModel, dataFileIndex=self.dataFileIndex,
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
        cacheKey = "%s,%s" % (self.folderModel.datasetModel.datasetId,
                              dataFilePath.encode('utf8'))
        with SETTINGS.updateCacheLock:
            SETTINGS.verifiedDatafilesCache[cacheKey] = True
        self.folderModel.SetDataFileUploaded(self.dataFileIndex, True)
        self.foldersModel.FolderStatusUpdated(self.folderModel)
        self.verificationsModel.SetComplete(self.verificationModel)
        PostEvent(self.foldersController.FoundVerifiedDatafileEvent(
            folderModel=self.folderModel, dataFileIndex=self.dataFileIndex,
            dataFilePath=dataFilePath))
        if self.testRun:
            message = "FOUND VERIFIED UPLOAD FOR: %s" \
                % self.folderModel.GetDataFileRelPath(self.dataFileIndex)
            logger.testrun(message)

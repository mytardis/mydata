"""
The main controller class for managing datafile verifications.

Most of this content used to be part of the FoldersController
class.
"""

import os
import threading
import traceback

import wx

from mydata.utils.openssh import GetBytesUploadedToStaging

from mydata.models.verification import VerificationModel
from mydata.models.verification import VerificationStatus
from mydata.models.datafile import DataFileModel
from mydata.controllers.uploads import UploadMethod
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import MultipleObjectsReturned
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
    def __init__(self, foldersController, foldersModel, folderModel,
                 dataFileIndex, settingsModel, testRun=False):
        # pylint: disable=too-many-arguments
        self.foldersController = foldersController
        self.foldersModel = foldersModel
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.settingsModel = settingsModel
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
        verificationsModel = self.foldersController.verificationsModel
        fc = self.foldersController  # pylint: disable=invalid-name
        if not hasattr(fc, "verificationsThreadingLock"):
            fc.verificationsThreadingLock = threading.Lock()
        fc.verificationsThreadingLock.acquire()
        verificationDataViewId = verificationsModel.GetMaxDataViewId() + 1
        self.verificationModel = \
            VerificationModel(dataViewId=verificationDataViewId,
                              folderModel=self.folderModel,
                              dataFileIndex=self.dataFileIndex)
        verificationsModel.AddRow(self.verificationModel)
        fc.verificationsThreadingLock.release()
        self.verificationModel.SetMessage("Looking for matching file on "
                                          "MyTardis server...")
        self.verificationModel.SetStatus(VerificationStatus.IN_PROGRESS)
        verificationsModel.VerificationMessageUpdated(self.verificationModel)

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
            verificationsModel\
                .VerificationMessageUpdated(self.verificationModel)
            self.HandleExistingDatafile(existingDatafile)
        except DoesNotExist, err:
            self.verificationModel.SetMessage("Didn't find datafile on "
                                              "MyTardis server.")
            self.verificationModel.SetStatus(VerificationStatus.NOT_FOUND)
            verificationsModel\
                .VerificationMessageUpdated(self.verificationModel)
            self.verificationModel.SetComplete()
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.didntFindDatafileOnServerEvent(
                    foldersController=self.foldersController,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    verificationModel=self.verificationModel))
        except MultipleObjectsReturned, err:
            self.folderModel.SetDataFileUploaded(self.dataFileIndex, True)
            self.foldersModel.FolderStatusUpdated(self.folderModel)
            self.verificationModel.SetComplete()
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.foundVerifiedDatafileEvent(
                    id=self.foldersController.EVT_FOUND_VERIFIED_DATAFILE,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    dataFilePath=dataFilePath))
            logger.error(err.GetMessage())
            raise
        except:  # pylint: disable=bare-except
            logger.error(traceback.format_exc())

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
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        replicas = existingDatafile.GetReplicas()
        message = "Found datafile record for %s " \
            "but it has no verified replicas." % dataFilePath
        logger.warning(message)
        message = "Found unverified datafile record on MyTardis."
        self.verificationModel.SetMessage(message)
        uploadToStagingRequest = self.settingsModel.GetUploadToStagingRequest()
        if self.foldersController.uploadMethod == \
                UploadMethod.VIA_STAGING and \
                uploadToStagingRequest is not None and \
                uploadToStagingRequest.IsApproved() and \
                len(replicas) > 0:
            # Can resume partial uploads:
            self.HandleExistingUnverifiedStagedDatafile(existingDatafile)
        else:
            # Can't resume partial uploads:
            self.HandleExistingUnverifiedPostedDatafile()

    def HandleExistingUnverifiedStagedDatafile(self, existingDatafile):
        """
        Can resume partial uploads.  We'll check whether this is a
        partial upload.
        """
        replicas = existingDatafile.GetReplicas()
        try:
            uploadToStagingRequest = self.settingsModel.GetUploadToStagingRequest()
            bytesUploadedToStaging = long(0)
            username = uploadToStagingRequest.GetScpUsername()
        except IncompatibleMyTardisVersion, err:
            self.verificationModel.SetComplete()
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
            self.verificationModel.SetComplete()
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
        bytesUploadedToStaging = long(0)
        try:
            bytesUploadedToStaging = \
                GetBytesUploadedToStaging(
                    remoteFilePath,
                    username, privateKeyFilePath, host, port,
                    self.settingsModel)
            logger.debug("%d bytes uploaded to staging for %s"
                         % (bytesUploadedToStaging,
                            replicas[0].GetUri()))
        except StagingHostRefusedSshConnection, err:
            self.verificationModel.SetComplete()
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
            self.verificationModel.SetComplete()
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
        if bytesUploadedToStaging == long(existingDatafile.GetSize()):
            self.HandleFullSizeUnverifiedStagedDatafile(existingDatafile)
        else:
            self.HandleIncompleteUnverifiedStagedDatafile(
                existingDatafile,
                bytesUploadedToStaging)

    def HandleFullSizeUnverifiedStagedDatafile(self, existingDatafile):
        """
        If the existing unverified DataFile upload is the correct size
        in staging, then we just need to wait for it to be verified.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        verificationsModel = self.foldersController.verificationsModel
        self.verificationModel\
            .SetMessage("Found unverified full-size datafile "
                        "on staging server.")
        self.verificationModel\
            .SetStatus(VerificationStatus
                       .FOUND_UNVERIFIED_FULL_SIZE)
        verificationsModel\
            .VerificationMessageUpdated(self.verificationModel)
        self.folderModel\
            .SetDataFileUploaded(self.dataFileIndex, True)
        self.foldersModel.FolderStatusUpdated(self.folderModel)
        self.verificationModel.SetComplete()
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
        wx.PostEvent(
            self.foldersController.notifyWindow,
            self.foldersController.unverifiedDatafileOnServerEvent(
                foldersController=self.foldersController,
                folderModel=self.folderModel,
                dataFileIndex=self.dataFileIndex,
                existingUnverifiedDatafile=existingDatafile,
                bytesUploadedToStaging=long(existingDatafile.GetSize()),
                verificationModel=self.verificationModel))

    def HandleIncompleteUnverifiedStagedDatafile(self, existingDatafile,
                                                 bytesUploadedToStaging):
        """
        Resume partial upload.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        verificationsModel = self.foldersController.verificationsModel
        self.verificationModel\
            .SetMessage("Found partially uploaded datafile "
                        "on staging server.")
        self.verificationModel\
            .SetStatus(VerificationStatus
                       .FOUND_UNVERIFIED_NOT_FULL_SIZE)
        verificationsModel\
            .VerificationMessageUpdated(self.verificationModel)
        logger.debug("Re-uploading \"%s\" to staging, because "
                     "the file size is %d bytes in staging, "
                     "but it should be %d bytes."
                     % (dataFilePath,
                        bytesUploadedToStaging,
                        long(existingDatafile.GetSize())))
        self.verificationModel.SetComplete()
        wx.PostEvent(
            self.foldersController.notifyWindow,
            self.foldersController.unverifiedDatafileOnServerEvent(
                foldersController=self.foldersController,
                folderModel=self.folderModel,
                dataFileIndex=self.dataFileIndex,
                existingUnverifiedDatafile=existingDatafile,
                bytesUploadedToStaging=bytesUploadedToStaging,
                verificationModel=self.verificationModel))

    def HandleExistingUnverifiedPostedDatafile(self):
        """
        Can't resume partial uploads.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        logger.debug("Found unverified datafile record for \"%s\" "
                     "on MyTardis while using HTTP POST for "
                     "uploads." % dataFilePath)
        self.verificationModel\
            .SetMessage("Found unverified datafile record. "
                        "You can wait for MyTardis to verify the "
                        "file, or if necessary, you can ask your "
                        "MyTardis administrator to delete the "
                        "file from the server, so you can "
                        "re-upload it.")
        self.verificationModel.SetComplete()
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

    def HandleExistingVerifiedDatafile(self):
        """
        Found existing verified file on server.
        """
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        self.folderModel.SetDataFileUploaded(self.dataFileIndex,
                                             True)
        self.foldersModel.FolderStatusUpdated(self.folderModel)
        self.verificationModel.SetComplete()
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

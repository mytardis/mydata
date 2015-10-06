"""
The main controller class for managing datafile verifications.

Most of this content used to be part of the FoldersController
class.
"""

# pylint: disable=missing-docstring

import os
import threading
import traceback

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

import wx


class VerifyDatafileRunnable(object):
    def __init__(self, foldersController, foldersModel, folderModel,
                 dataFileIndex, settingsModel):
        # pylint: disable=too-many-arguments
        self.foldersController = foldersController
        self.foldersModel = foldersModel
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.settingsModel = settingsModel
        self.verificationModel = None

    def GetDatafileIndex(self):
        return self.dataFileIndex

    def Run(self):
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements

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

        existingDatafile = None
        # pylint: disable=bare-except
        try:
            existingDatafile = DataFileModel.GetDataFile(
                settingsModel=self.settingsModel,
                dataset=self.folderModel.GetDatasetModel(),
                filename=dataFileName,
                directory=dataFileDirectory)
            self.verificationModel.SetMessage("Found datafile on "
                                              "MyTardis server.")
            self.verificationModel.SetStatus(VerificationStatus.FOUND_VERIFIED)
            verificationsModel\
                .VerificationMessageUpdated(self.verificationModel)
        except DoesNotExist, err:
            self.verificationModel.SetMessage("Didn't find datafile on "
                                              "MyTardis server.")
            self.verificationModel.SetStatus(VerificationStatus.NOT_FOUND)
            verificationsModel\
                .VerificationMessageUpdated(self.verificationModel)
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
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.foundVerifiedDatafileEvent(
                    id=self.foldersController.EVT_FOUND_VERIFIED_DATAFILE,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    dataFilePath=dataFilePath))
            logger.error(err.GetMessage())
            raise
        except:
            logger.error(traceback.format_exc())

        if existingDatafile:
            replicas = existingDatafile.GetReplicas()
            if len(replicas) == 0 or not replicas[0].IsVerified():
                message = "Found datafile record for %s " \
                    "but it has no verified replicas." % dataFilePath
                logger.warning(message)
                message = "Found unverified datafile record on MyTardis."
                self.verificationModel.SetMessage(message)
                # logger.debug(str(existingDatafile.GetJson()))
                uploadToStagingRequest = self.settingsModel\
                    .GetUploadToStagingRequest()
                bytesUploadedToStaging = 0
                if self.foldersController.uploadMethod == \
                        UploadMethod.VIA_STAGING and \
                        uploadToStagingRequest is not None and \
                        uploadToStagingRequest.IsApproved() and \
                        len(replicas) > 0:
                    try:
                        username = uploadToStagingRequest.GetScpUsername()
                    except IncompatibleMyTardisVersion, err:
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
                        self.verificationModel.SetComplete()
                        return
                    except StorageBoxAttributeNotFound, err:
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
                        self.verificationModel.SetComplete()
                        return
                    privateKeyFilePath = self.settingsModel\
                        .GetSshKeyPair().GetPrivateKeyFilePath()
                    host = uploadToStagingRequest.GetScpHostname()
                    port = uploadToStagingRequest.GetScpPort()
                    location = uploadToStagingRequest.GetLocation()
                    remoteFilePath = "%s/%s" % (location.rstrip('/'),
                                                replicas[0].GetUri())
                    bytesUploadedToStaging = 0
                    try:
                        bytesUploadedToStaging = \
                            GetBytesUploadedToStaging(
                                remoteFilePath,
                                username, privateKeyFilePath, host, port)
                        logger.debug("%d bytes uploaded to staging for %s"
                                     % (bytesUploadedToStaging,
                                        replicas[0].GetUri()))
                    except StagingHostRefusedSshConnection, err:
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
                        self.verificationModel.SetComplete()
                        return
                    except StagingHostSshPermissionDenied, err:
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
                        self.verificationModel.SetComplete()
                        return
                    if bytesUploadedToStaging == \
                            int(existingDatafile.GetSize()):
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
                        wx.PostEvent(
                            self.foldersController.notifyWindow,
                            self.foldersController
                            .foundUnverifiedDatafileEvent(
                                id=self.foldersController
                                .EVT_FOUND_UNVERIFIED_BUT_FULL_SIZE_DATAFILE,
                                folderModel=self.folderModel,
                                dataFileIndex=self.dataFileIndex,
                                dataFilePath=dataFilePath))
                        self.verificationModel.SetComplete()
                        return
                    else:
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
                                        int(existingDatafile.GetSize())))
                    wx.PostEvent(
                        self.foldersController.notifyWindow,
                        self.foldersController.unverifiedDatafileOnServerEvent(
                            foldersController=self.foldersController,
                            folderModel=self.folderModel,
                            dataFileIndex=self.dataFileIndex,
                            existingUnverifiedDatafile=existingDatafile,
                            bytesUploadedToStaging=bytesUploadedToStaging,
                            verificationModel=self.verificationModel))
                else:
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
            else:
                self.folderModel.SetDataFileUploaded(self.dataFileIndex,
                                                     True)
                self.foldersModel.FolderStatusUpdated(self.folderModel)
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.foundVerifiedDatafileEvent(
                        id=self.foldersController.EVT_FOUND_VERIFIED_DATAFILE,
                        folderModel=self.folderModel,
                        dataFileIndex=self.dataFileIndex,
                        dataFilePath=dataFilePath))
        self.verificationModel.SetComplete()

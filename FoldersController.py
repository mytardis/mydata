import os
import sys
import threading
import urllib
import urllib2
import requests
import json
import Queue
import io
import traceback
from datetime import datetime
import mimetypes
import time
import subprocess
import hashlib
import poster

import OpenSSH

from ExperimentModel import ExperimentModel
from DatasetModel import DatasetModel
from UserModel import UserModel
from VerificationModel import VerificationModel
from VerificationModel import VerificationStatus
from UploadModel import UploadModel
from UploadModel import UploadStatus
from FolderModel import FolderModel
from DataFileModel import DataFileModel
from Exceptions import DoesNotExist
from Exceptions import MultipleObjectsReturned
from Exceptions import Unauthorized
from Exceptions import InternalServerError
from Exceptions import StagingHostRefusedSshConnection
from Exceptions import StagingHostSshPermissionDenied
from Exceptions import ScpException

from logger.Logger import logger

import wx
import wx.lib.newevent
import wx.dataview

from DragAndDrop import MyFolderDropTarget
from AddFolderDialog import AddFolderDialog


class ConnectionStatus():
    CONNECTED = 0
    DISCONNECTED = 1


class UploadMethod():
    HTTP_POST = 0
    VIA_STAGING = 1


class FoldersController():
    def __init__(self, notifyWindow, foldersModel, foldersView, usersModel,
                 verificationsModel, uploadsModel, settingsModel):
        self.notifyWindow = notifyWindow
        self.foldersModel = foldersModel
        self.foldersView = foldersView
        self.usersModel = usersModel
        self.verificationsModel = verificationsModel
        self.uploadsModel = uploadsModel
        self.settingsModel = settingsModel

        self.shuttingDown = threading.Event()
        self.showingErrorDialog = threading.Event()
        self.showingWarningDialog = threading.Event()
        self.canceled = threading.Event()
        self.failed = threading.Event()

        # These will get overwritten in UploadDataThread, but we need
        # to initialize them here, so that ShutDownUploadThreads()
        # can be called.
        self.numVerificationWorkerThreads = 0
        self.verificationWorkerThreads = []
        self.numUploadWorkerThreads = 0
        self.uploadWorkerThreads = []

        self.lastUsedFolderType = None
        self.folderDropTarget = MyFolderDropTarget(self)
        self.foldersView.SetDropTarget(self.folderDropTarget)

        self.foldersView.Bind(wx.EVT_BUTTON, self.OnOpenFolder,
                              self.foldersView.GetOpenFolderButton())
        self.foldersView.GetDataViewControl()\
            .Bind(wx.dataview.EVT_DATAVIEW_ITEM_ACTIVATED, self.OnOpenFolder)

        self.DidntFindMatchingDatafileOnServerEvent, eventBinder = \
            wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(eventBinder, self.UploadDatafile)

        self.UnverifiedDatafileOnServerEvent, eventBinder = \
            wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(eventBinder, self.UploadDatafile)

        self.ConnectionStatusEvent, eventBinder = wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(eventBinder,  self.UpdateStatusBar)

        self.ShowMessageDialogEvent, eventBinder = wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(eventBinder, self.ShowMessageDialog)

        self.ShutdownUploadsEvent, eventBinder = wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(eventBinder, self.ShutDownUploadThreads)

        self.FoundVerifiedDatafileEvent, eventBinder = \
            wx.lib.newevent.NewCommandEvent()
        self.EVT_FOUND_VERIFIED_DATAFILE = wx.NewId()
        self.notifyWindow.Bind(eventBinder,
                               self.CountCompletedUploadsAndVerifications)

        self.FoundUnverifiedButFullSizeDatafileEvent, eventBinder = \
            wx.lib.newevent.NewCommandEvent()
        self.EVT_FOUND_UNVERIFIED_BUT_FULL_SIZE_DATAFILE = wx.NewId()
        self.notifyWindow.Bind(eventBinder,
                               self.CountCompletedUploadsAndVerifications)

        self.UploadCompleteEvent, eventBinder = \
            wx.lib.newevent.NewCommandEvent()
        self.EVT_UPLOAD_COMPLETE = wx.NewId()
        self.notifyWindow.Bind(eventBinder,
                               self.CountCompletedUploadsAndVerifications)

    def Canceled(self):
        return self.canceled.isSet()

    def SetCanceled(self, canceled=True):
        if canceled:
            self.canceled.set()
        else:
            self.canceled.clear()

    def Failed(self):
        return self.failed.isSet()

    def SetFailed(self, failed=True):
        if failed:
            self.failed.set()
        else:
            self.failed.clear()

    def Completed(self):
        return self.completed

    def SetCompleted(self, completed=True):
        self.completed = completed

    def IsShuttingDown(self):
        return self.shuttingDown.isSet()

    def SetShuttingDown(self, shuttingDown=True):
        if shuttingDown:
            self.shuttingDown.set()
        else:
            self.shuttingDown.clear()

    def IsShowingErrorDialog(self):
        return self.showingErrorDialog.isSet()

    def SetShowingErrorDialog(self, showingErrorDialog=True):
        if showingErrorDialog:
            self.showingErrorDialog.set()
        else:
            self.showingErrorDialog.clear()

    def UpdateStatusBar(self, event):
        if event.connectionStatus == ConnectionStatus.CONNECTED:
            self.notifyWindow.SetConnected(event.myTardisUrl, True)
        else:
            self.notifyWindow.SetConnected(event.myTardisUrl, False)

    def ShowMessageDialog(self, event):
        if self.IsShowingErrorDialog():
            logger.warning("Refusing to show message dialog for message "
                           "\"%s\" because we are already showing an error "
                           "dialog." % event.message)
            return
        if event.icon == wx.ICON_ERROR:
            self.SetShowingErrorDialog(True)
        dlg = wx.MessageDialog(None, event.message, event.title,
                               wx.OK | event.icon)
        try:
            wx.EndBusyCursor()
            needToRestartBusyCursor = True
        except:
            needToRestartBusyCursor = False
        dlg.ShowModal()
        if needToRestartBusyCursor:
            wx.BeginBusyCursor()
        if event.icon == wx.ICON_ERROR:
            self.SetShowingErrorDialog(False)

    def UploadDatafile(self, event):
        """
        This method runs in the main thread, so it shouldn't do anything
        time-consuming or blocking, unless it launches another thread.
        Because this method adds upload tasks to a queue, it is important
        to note that if the queue has a maxsize set, then an attempt to
        add something to the queue could block the GUI thread, making the
        application appear unresponsive.
        """
        if self.IsShuttingDown():
            return
        before = datetime.now()
        folderModel = event.folderModel
        foldersController = event.foldersController
        dfi = event.dataFileIndex
        uploadsModel = foldersController.uploadsModel

        if folderModel not in foldersController.uploadDatafileRunnable:
            foldersController.uploadDatafileRunnable[folderModel] = {}

        if not hasattr(self, "uploadsThreadingLock"):
            self.uploadsThreadingLock = threading.Lock()
        self.uploadsThreadingLock.acquire()
        uploadDataViewId = uploadsModel.GetMaxDataViewId() + 1
        uploadModel = UploadModel(dataViewId=uploadDataViewId,
                                  folderModel=folderModel,
                                  dataFileIndex=dfi)
        uploadsModel.AddRow(uploadModel)
        self.uploadsThreadingLock.release()
        if hasattr(event, "bytesUploadedToStaging"):
            uploadModel.SetBytesUploadedToStaging(event.bytesUploadedToStaging)
        uploadModel.SetVerificationModel(event.verificationModel)
        if self.IsShuttingDown():
            return
        existingUnverifiedDatafile = False
        if hasattr(event, "existingUnverifiedDatafile"):
            existingUnverifiedDatafile = event.existingUnverifiedDatafile
        foldersController.uploadDatafileRunnable[folderModel][dfi] = \
            UploadDatafileRunnable(self, self.foldersModel, folderModel,
                                   dfi, self.uploadsModel, uploadModel,
                                   self.settingsModel,
                                   existingUnverifiedDatafile)
        if self.IsShuttingDown():
            return
        self.uploadsQueue.put(foldersController
                              .uploadDatafileRunnable[folderModel][dfi])
        after = datetime.now()
        duration = after - before
        if duration.total_seconds() >= 1:
            logger.warning("UploadDatafile for " +
                           folderModel.GetDataFileName(dfi) +
                           " blocked the main GUI thread for %d seconds." +
                           duration.total_seconds())

    def StartDataUploads(self):
        fc = self
        settingsModel = fc.settingsModel
        fc.canceled.clear()
        fc.verificationsModel.DeleteAllRows()
        fc.verifyDatafileRunnable = {}
        fc.verificationsQueue = Queue.Queue()
        # For now, the max number of verification threads is set to be the
        # same as the max number of upload threads.
        fc.numVerificationWorkerThreads = settingsModel.GetMaxUploadThreads()
        fc.verificationWorkerThreads = []

        for i in range(fc.numVerificationWorkerThreads):
            t = threading.Thread(name="VerificationWorkerThread-%d"
                                 % (i+1),
                                 target=fc.verificationWorker,
                                 args=(i+1,))
            fc.verificationWorkerThreads.append(t)
            t.start()
        fc.uploadDatafileRunnable = {}
        fc.uploadsQueue = Queue.Queue()
        fc.numUploadWorkerThreads = settingsModel.GetMaxUploadThreads()
        fc.uploadMethod = UploadMethod.HTTP_POST

        settingsModel.GetUploaderModel().RequestStagingAccess()
        uploadToStagingRequest = settingsModel\
            .GetUploadToStagingRequest()
        message = None
        if uploadToStagingRequest is None:
            message = "Couldn't determine whether uploads to " \
                      "staging have been approved.  " \
                      "Falling back to HTTP POST."
        elif uploadToStagingRequest['approved']:
            logger.info("Uploads to staging have been approved.")
            fc.uploadMethod = UploadMethod.VIA_STAGING
        else:
            message = \
                "Uploads to MyTardis's staging area require " \
                "approval from your MyTardis administrator.\n\n" \
                "A request has been sent, and you will be contacted " \
                "once the request has been approved. Until then, " \
                "MyData will upload files using HTTP POST, and will " \
                "only upload one file at a time.\n\n" \
                "HTTP POST is generally only suitable for small " \
                "files (up to 100 MB each)."
        if message:
            logger.warning(message)
            wx.PostEvent(
                self.notifyWindow,
                self.ShowMessageDialogEvent(
                    title="MyData",
                    message=message,
                    icon=wx.ICON_WARNING))
            fc.uploadMethod = UploadMethod.HTTP_POST
        if fc.uploadMethod == UploadMethod.HTTP_POST and \
                fc.numUploadWorkerThreads > 1:
            logger.warning(
                "Using HTTP POST, so setting "
                "numUploadWorkerThreads to 1, "
                "because urllib2 is not thread-safe.")
            fc.numUploadWorkerThreads = 1

        fc.uploadWorkerThreads = []
        for i in range(fc.numUploadWorkerThreads):
            t = threading.Thread(name="UploadWorkerThread-%d" % (i+1),
                                 target=fc.uploadWorker, args=())
            fc.uploadWorkerThreads.append(t)
            t.start()
        try:
            fc.numVerificationsToBePerformed = 0
            fc.finishedCountingNumVerificationsToBePerformed = \
                threading.Event()
            for row in range(0, self.foldersModel.GetRowCount()):
                if self.IsShuttingDown():
                    return
                folderModel = self.foldersModel.foldersData[row]
                fc.numVerificationsToBePerformed += folderModel.GetNumFiles()
                logger.debug(
                    "UploadDataThread: Starting verifications "
                    "and uploads for folder: " +
                    folderModel.GetFolder())
                if self.IsShuttingDown():
                    return
                try:
                    # Save MyTardis URL, so if it's changing in the
                    # Settings Dialog while this thread is
                    # attempting to connect, we ensure that any
                    # exception thrown by this thread refers to the
                    # old version of the URL.
                    myTardisUrl = \
                        settingsModel.GetMyTardisUrl()
                    try:
                        experimentModel = ExperimentModel\
                            .GetOrCreateExperimentForFolder(folderModel)
                    except Exception, e:
                        logger.error(traceback.format_exc())
                        wx.PostEvent(
                            self.notifyWindow,
                            self.ShowMessageDialogEvent(
                                title="MyData",
                                message=str(e),
                                icon=wx.ICON_ERROR))
                        return
                    folderModel.SetExperiment(experimentModel)
                    CONNECTED = ConnectionStatus.CONNECTED
                    wx.PostEvent(
                        self.notifyWindow,
                        self.ConnectionStatusEvent(
                            myTardisUrl=myTardisUrl,
                            connectionStatus=CONNECTED))
                    try:
                        datasetModel = DatasetModel\
                            .CreateDatasetIfNecessary(folderModel)
                    except Exception, e:
                        logger.error(traceback.format_exc())
                        wx.PostEvent(
                            self.notifyWindow,
                            self.ShowMessageDialogEvent(
                                title="MyData",
                                message=str(e),
                                icon=wx.ICON_ERROR))
                        return
                    folderModel.SetDatasetModel(datasetModel)
                    self.VerifyDatafiles(folderModel)
                except requests.exceptions.ConnectionError, e:
                    if not self.IsShuttingDown():
                        DISCONNECTED = \
                            ConnectionStatus.DISCONNECTED
                        wx.PostEvent(
                            self.notifyWindow,
                            self.ConnectionStatusEvent(
                                myTardisUrl=myTardisUrl,
                                connectionStatus=DISCONNECTED))
                    return
                except ValueError, e:
                    logger.debug("Failed to retrieve experiment "
                                 "for folder " +
                                 str(folderModel.GetFolder()))
                    logger.debug(traceback.format_exc())
                    return
                if experimentModel is None:
                    logger.debug("Failed to acquire a MyTardis "
                                 "experiment to store data in for"
                                 "folder " +
                                 folderModel.GetFolder())
                    return
                if self.IsShuttingDown():
                    return
            fc.finishedCountingNumVerificationsToBePerformed.set()
            # End: for row in range(0, self.foldersModel.GetRowCount())
        except:
            logger.error(traceback.format_exc())

    def uploadWorker(self):
        """
        One worker per thread
        By default, up to 5 threads can run simultaneously
        for uploading local data files to
        the MyTardis server.
        """
        while True:
            if self.IsShuttingDown():
                return
            task = self.uploadsQueue.get()
            if task is None:
                if self.Failed():
                    success, failed, canceled = False, True, False
                elif self.Canceled():
                    success, failed, canceled = False, False, True
                else:
                    success, failed, canceled = True, False, False
                return
            try:
                task.run()
            except ValueError, e:
                if str(e) == "I/O operation on closed file":
                    logger.info(
                        "Ignoring closed file exception - it is normal "
                        "to encounter these exceptions while canceling "
                        "uploads.")
                    self.uploadsQueue.task_done()
                    return
                else:
                    logger.error(traceback.format_exc())
                    self.uploadsQueue.task_done()
                    return
            except:
                logger.error(traceback.format_exc())
                self.uploadsQueue.task_done()
                return

    def verificationWorker(self, verificationWorkerId):
        """
        One worker per thread.
        By default, up to 5 threads can run simultaneously
        for verifying whether local data files exist on
        the MyTardis server.
        """
        while True:
            if self.IsShuttingDown():
                return
            task = self.verificationsQueue.get()
            if task is None:
                break
            try:
                task.run()
            except ValueError, e:
                if str(e) == "I/O operation on closed file":
                    logger.info(
                        "Ignoring closed file exception - it is normal "
                        "to encounter these exceptions while canceling "
                        "uploads.")
                    self.verificationsQueue.task_done()
                    return
                else:
                    logger.error(traceback.format_exc())
                    self.verificationsQueue.task_done()
                    return
            except:
                logger.error(traceback.format_exc())
                self.verificationsQueue.task_done()
                return

    def CountCompletedUploadsAndVerifications(self, event):
        """
        Check if we have finished uploads and verifications,
        and if so, call ShutDownUploadThreads
        """
        numFilesFoundVerified = self.verificationsModel.GetFoundVerifiedCount()
        numFilesNotFound = self.verificationsModel.GetNotFoundCount()
        numFilesFoundUnverifiedFullSize = \
            self.verificationsModel.GetFoundUnverifiedFullSizeCount()
        numFilesFoundUnverifiedNotFullSize = \
            self.verificationsModel.GetFoundUnverifiedNotFullSizeCount()

        numVerificationsProcessed = \
            numFilesFoundVerified + \
            numFilesNotFound + \
            numFilesFoundUnverifiedFullSize + \
            numFilesFoundUnverifiedNotFullSize

        numVerificationsCompleted = self.verificationsModel.GetCompletedCount()

        uploadsToBePerformed = self.uploadsModel.GetRowCount()
        uploadsCompleted = self.uploadsModel.GetCompletedCount()
        uploadsFailed = self.uploadsModel.GetFailedCount()
        uploadsProcessed = uploadsCompleted + uploadsFailed

        if numVerificationsCompleted == self.numVerificationsToBePerformed \
                and self.finishedCountingNumVerificationsToBePerformed.isSet() \
                and uploadsProcessed == uploadsToBePerformed:
            logger.debug("All datafile verifications and uploads "
                         "have completed.")
            logger.debug("Shutting down upload and verification threads.")
            wx.PostEvent(self.notifyWindow,
                         self.ShutdownUploadsEvent(completed=True))

    def ShutDownUploadThreads(self, event=None):
        if self.IsShuttingDown():
            return
        self.SetShuttingDown(True)
        logger.debug("Shutting down uploads threads...")
        if hasattr(event, "failed") and event.failed:
            self.SetFailed()
            self.uploadsModel.CancelRemaining()
        elif hasattr(event, "completed") and event.completed:
            self.SetCompleted()
        else:
            self.SetCanceled()
        if hasattr(self, 'uploadDataThread'):
            logger.debug("Joining FoldersController's UploadDataThread...")
            self.uploadDataThread.join()
            logger.debug("Joined FoldersController's UploadDataThread.")
        logger.debug("Shutting down FoldersController upload worker threads.")
        for i in range(self.numUploadWorkerThreads):
            self.uploadsQueue.put(None)
        for t in self.uploadWorkerThreads:
            t.join()
        logger.debug("Shutting down FoldersController verification "
                     "worker threads.")
        for i in range(self.numVerificationWorkerThreads):
            self.verificationsQueue.put(None)
        for t in self.verificationWorkerThreads:
            t.join()

        self.verifyDatafileRunnable = {}
        self.uploadDatafileRunnable = {}

        if self.Failed():
            logger.info("Data scan and uploads failed.")
        elif self.Canceled():
            logger.info("Data scan and uploads were canceled.")
        elif self.Completed():
            logger.info("Data scan and uploads completed successfully.")
        else:
            logger.info("Data scan and uploads appear to have "
                        "completed successfully.")

        self.notifyWindow.SetOnRefreshRunning(False)
        self.SetShuttingDown(False)

        try:
            wx.EndBusyCursor()
        except:
            pass

        logger.debug("")

    def OnDropFiles(self, filepaths):
        if len(filepaths) == 1 and self.foldersModel.Contains(filepaths[0]):
            message = "This folder has already been added."
            dlg = wx.MessageDialog(None, message, "Add Folder(s)",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            return
        allFolders = True
        folderType = None
        folderModelsAdded = []
        for filepath in filepaths:

            if not os.path.isdir(filepath):
                message = filepath + " is not a folder."
                dlg = wx.MessageDialog(None, message, "Add Folder(s)",
                                       wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                return
            elif not self.foldersModel.Contains(filepath):
                (location, folder) = os.path.split(filepath)

                dataViewId = self.foldersModel.GetMaxDataViewId() + 1
                if folderType is None:

                    usersModel = self.usersModel
                    addFolderDialog = \
                        AddFolderDialog(self.notifyWindow, -1,
                                        "Add Folder(s)", usersModel,
                                        size=(350, 200),
                                        style=wx.DEFAULT_DIALOG_STYLE)

                    addFolderDialog.CenterOnParent()

                    if addFolderDialog.ShowModal() == wx.ID_OK:
                        folderType = addFolderDialog.GetFolderType()
                        self.lastUsedFolderType = folderType
                    else:
                        return

                usersModel = self.usersModel
                owner = \
                    usersModel.GetUserByName(addFolderDialog.GetOwnerName())
                settingsModel = self.foldersModel.GetSettingsModel()
                folderModel = FolderModel(dataViewId=dataViewId, folder=folder,
                                          location=location,
                                          folder_type=self.lastUsedFolderType,
                                          owner=owner,
                                          foldersModel=self.foldersModel,
                                          usersModel=usersModel,
                                          settingsModel=settingsModel)
                self.foldersModel.AddRow(folderModel)
                folderModelsAdded.append(folderModel)

        self.StartDataUploads(folderModels=folderModelsAdded)

    def VerifyDatafiles(self, folderModel):
        if folderModel not in self.verifyDatafileRunnable:
            self.verifyDatafileRunnable[folderModel] = []
        for dfi in range(0, folderModel.numFiles):
            if self.IsShuttingDown():
                return
            thisFileIsAlreadyBeingVerified = False
            for existingVerifyDatafileRunnable in \
                    self.verifyDatafileRunnable[folderModel]:
                if dfi == existingVerifyDatafileRunnable.GetDatafileIndex():
                    thisFileIsAlreadyBeingVerified = True
            thisFileIsAlreadyBeingUploaded = False
            if folderModel in self.uploadDatafileRunnable:
                if dfi in self.uploadDatafileRunnable[folderModel]:
                    thisFileIsAlreadyBeingUploaded = True
            if not thisFileIsAlreadyBeingVerified \
                    and not thisFileIsAlreadyBeingUploaded:
                self.verifyDatafileRunnable[folderModel]\
                    .append(VerifyDatafileRunnable(self, self.foldersModel,
                                                   folderModel, dfi,
                                                   self.settingsModel))
                self.verificationsQueue\
                    .put(self.verifyDatafileRunnable[folderModel][dfi])

    def OnAddFolder(self, evt):
        dlg = wx.DirDialog(self.notifyWindow, "Choose a directory:")
        if dlg.ShowModal() == wx.ID_OK:
            self.OnDropFiles([dlg.GetPath(), ])

    def OnDeleteFolders(self, evt):
        # Remove the selected row(s) from the model. The model will take care
        # of notifying the view (and any other observers) that the change has
        # happened.
        items = self.foldersView.GetDataViewControl().GetSelections()
        rows = [self.foldersModel.GetRow(item) for item in items]
        if len(rows) > 1:
            message = "Are you sure you want to remove the selected folders?"
        elif len(rows) == 1:
            message = "Are you sure you want to remove the \"" + \
                self.foldersModel\
                .GetValueForRowColumnKeyName(rows[0], "folder") + \
                "\" folder?"
        else:
            dlg = wx.MessageDialog(self.notifyWindow,
                                   "Please select a folder to delete.",
                                   "Delete Folder(s)", wx.OK)
            dlg.ShowModal()
            return
        confirmationDialog = \
            wx.MessageDialog(self.notifyWindow, message, "Confirm Delete",
                             wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        okToDelete = confirmationDialog.ShowModal()
        if okToDelete == wx.ID_OK:
            self.foldersModel.DeleteRows(rows)

    def OnOpenFolder(self, evt):
        items = self.foldersView.GetDataViewControl().GetSelections()
        rows = [self.foldersModel.GetRow(item) for item in items]
        if len(rows) != 1:
            if len(rows) > 1:
                message = "Please select a single folder."
            else:
                message = "Please select a folder to open."
            dlg = wx.MessageDialog(self.notifyWindow, message, "Open Folder",
                                   wx.OK)
            dlg.ShowModal()
            return
        row = rows[0]

        path = os.path.join(self.foldersModel
                            .GetValueForRowColumnKeyName(row, "location"),
                            self.foldersModel
                            .GetValueForRowColumnKeyName(row, "folder"))
        if not os.path.exists(path):
            message = "Path doesn't exist: " + path
            dlg = wx.MessageDialog(None, message, "Open Folder", wx.OK)
            dlg.ShowModal()
            return
        if sys.platform == 'darwin':
            def openFolder(path):
                subprocess.check_call(['open', '--', path])
        elif sys.platform.startswith('linux'):
            def openFolder(path):
                subprocess.check_call(['xdg-open', '--', path])
        elif sys.platform.startswith('win'):
            def openFolder(path):
                subprocess.call(['explorer', path])
        else:
            logger.debug("sys.platform = " + sys.platform)

        openFolder(path)

    def CalculateMd5Sum(self, filePath, fileSize, uploadModel,
                        ProgressCallback=None):
        md5 = hashlib.md5()

        defaultChunkSize = 128*1024  # FIXME: magic number
        maxChunkSize = 256*1024*1024  # FIXME: magic number
        chunkSize = defaultChunkSize
        # FIXME: magic number (approximately 50 progress bar increments)
        while (fileSize / chunkSize) > 50 and chunkSize < maxChunkSize:
            chunkSize = chunkSize * 2
        bytesProcessed = 0
        with open(filePath, 'rb') as f:
            # Note that the iter() func needs an empty byte string
            # for the returned iterator to halt at EOF, since read()
            # returns b'' (not just '').
            for chunk in iter(lambda: f.read(chunkSize), b''):
                if self.IsShuttingDown() or uploadModel.Canceled():
                    logger.debug("Aborting MD5 calculation for "
                                 "%s" % filePath)
                    return None
                md5.update(chunk)
                bytesProcessed += len(chunk)
                if ProgressCallback:
                    ProgressCallback(bytesProcessed)
        return md5.hexdigest()


class VerifyDatafileRunnable():
    def __init__(self, foldersController, foldersModel, folderModel,
                 dataFileIndex, settingsModel):
        self.foldersController = foldersController
        self.foldersModel = foldersModel
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.settingsModel = settingsModel

    def GetDatafileIndex(self):
        return self.dataFileIndex

    def run(self):
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileDirectory = \
            self.folderModel.GetDataFileDirectory(self.dataFileIndex)
        dataFileName = os.path.basename(dataFilePath)
        verificationsModel = self.foldersController.verificationsModel
        fc = self.foldersController
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
        except DoesNotExist, e:
            self.verificationModel.SetMessage("Didn't find datafile on "
                                              "MyTardis server.")
            self.verificationModel.SetStatus(VerificationStatus.NOT_FOUND)
            verificationsModel\
                .VerificationMessageUpdated(self.verificationModel)
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.DidntFindMatchingDatafileOnServerEvent(
                    foldersController=self.foldersController,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    verificationModel=self.verificationModel))
        except MultipleObjectsReturned, e:
            self.folderModel.SetDataFileUploaded(self.dataFileIndex, True)
            self.foldersModel.FolderStatusUpdated(self.folderModel)
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.FoundVerifiedDatafileEvent(
                    id=self.foldersController.EVT_FOUND_VERIFIED_DATAFILE,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    dataFilePath=dataFilePath))
            logger.error(e.GetMessage())
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
                        uploadToStagingRequest['approved'] and \
                        len(replicas) > 0:
                    username = uploadToStagingRequest['approved_username']
                    privateKeyFilePath = self.settingsModel\
                        .GetSshKeyPair().GetPrivateKeyFilePath()
                    hostJson = \
                        uploadToStagingRequest['approved_staging_host']
                    host = hostJson['host']
                    bytesUploadedToStaging = 0
                    try:
                        bytesUploadedToStaging = \
                            OpenSSH.GetBytesUploadedToStaging(
                                replicas[0].GetUri(),
                                username, privateKeyFilePath, host,
                                self.verificationModel)
                        logger.debug("%d bytes uploaded to staging for %s"
                                     % (bytesUploadedToStaging,
                                        replicas[0].GetUri()))
                    except StagingHostRefusedSshConnection, e:
                        wx.PostEvent(
                            self.foldersController.notifyWindow,
                            self.foldersController.ShutdownUploadsEvent(
                                failed=True))
                        message = str(e)
                        wx.PostEvent(
                            self.foldersController.notifyWindow,
                            self.foldersController
                                .ShowMessageDialogEvent(
                                    title="MyData",
                                    message=message,
                                    icon=wx.ICON_ERROR))
                        self.verificationModel.SetComplete()
                        return
                    except StagingHostSshPermissionDenied, e:
                        wx.PostEvent(
                            self.foldersController.notifyWindow,
                            self.foldersController.ShutdownUploadsEvent(
                                failed=True))
                        message = str(e)
                        wx.PostEvent(
                            self.foldersController.notifyWindow,
                            self.foldersController
                                .ShowMessageDialogEvent(
                                    title="MyData",
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
                                .FoundUnverifiedButFullSizeDatafileEvent(
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
                        self.foldersController.UnverifiedDatafileOnServerEvent(
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
                    self.foldersController.FoundVerifiedDatafileEvent(
                        id=self.foldersController.EVT_FOUND_VERIFIED_DATAFILE,
                        folderModel=self.folderModel,
                        dataFileIndex=self.dataFileIndex,
                        dataFilePath=dataFilePath))
        self.verificationModel.SetComplete()


class UploadDatafileRunnable():
    def __init__(self, foldersController, foldersModel, folderModel,
                 dataFileIndex, uploadsModel, uploadModel, settingsModel,
                 existingUnverifiedDatafile):
        self.foldersController = foldersController
        self.foldersModel = foldersModel
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.uploadsModel = uploadsModel
        self.uploadModel = uploadModel
        self.settingsModel = settingsModel
        self.existingUnverifiedDatafile = existingUnverifiedDatafile

    def GetDatafileIndex(self):
        return self.dataFileIndex

    def run(self):
        if self.uploadModel.Canceled():
            # self.foldersController.SetCanceled()
            logger.debug("Upload for \"%s\" was canceled "
                         "before it began uploading." %
                         self.uploadModel.GetRelativePathToUpload())
            return
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileName = os.path.basename(dataFilePath)
        dataFileDirectory = \
            self.folderModel.GetDataFileDirectory(self.dataFileIndex)
        datasetId = self.folderModel.GetDatasetModel().GetId()

        thirtySeconds = 30
        if (time.time() - os.path.getmtime(dataFilePath)) <= thirtySeconds:
            message = "Not uploading file, in case it is still being modified."
            self.uploadModel.SetMessage(message)
            self.uploadsModel.UploadMessageUpdated(self.uploadModel)
            self.uploadModel.SetStatus(UploadStatus.FAILED)
            self.uploadsModel.UploadStatusUpdated(self.uploadModel)
            return

        logger.debug("Uploading " +
                     self.folderModel.GetDataFileName(self.dataFileIndex) +
                     "...")

        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST or \
                not self.existingUnverifiedDatafile:
            myTardisUrl = self.settingsModel.GetMyTardisUrl()
            myTardisUsername = self.settingsModel.GetUsername()
            myTardisApiKey = self.settingsModel.GetApiKey()
            url = myTardisUrl + "/api/v1/dataset_file/"
            headers = {"Authorization": "ApiKey " + myTardisUsername + ":" +
                       myTardisApiKey}

        if self.foldersController.IsShuttingDown():
            return

        self.uploadModel.SetMessage("Getting data file size...")
        dataFileSize = self.folderModel.GetDataFileSize(self.dataFileIndex)
        self.uploadModel.SetFileSize(dataFileSize)

        if self.foldersController.IsShuttingDown():
            return

        # The HTTP POST upload method doesn't support resuming uploads,
        # so we always (re-)create the JSON to be POSTed when we find
        # a file whose datafile record is unverified.

        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST or \
                not self.existingUnverifiedDatafile:
            self.uploadModel.SetMessage("Calculating MD5 checksum...")

            def Md5ProgressCallback(bytesProcessed):
                if self.uploadModel.Canceled():
                    # self.foldersController.SetCanceled()
                    return
                percentComplete = \
                    100.0 - ((dataFileSize - bytesProcessed) * 100.0) \
                    / dataFileSize

                # self.uploadModel.SetProgress(float(percentComplete))
                self.uploadModel.SetProgress(int(percentComplete))
                self.uploadsModel.UploadProgressUpdated(self.uploadModel)
                if dataFileSize >= (1024 * 1024 * 1024):
                    self.uploadModel.SetMessage("%3.1f %%  MD5 summed"
                                                % percentComplete)
                else:
                    self.uploadModel.SetMessage("%3d %%  MD5 summed"
                                                % int(percentComplete))
                self.uploadsModel.UploadMessageUpdated(self.uploadModel)
                myTardisUrl = self.settingsModel.GetMyTardisUrl()
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.ConnectionStatusEvent(
                        myTardisUrl=myTardisUrl,
                        connectionStatus=ConnectionStatus.CONNECTED))
            dataFileMd5Sum = \
                self.foldersController\
                    .CalculateMd5Sum(dataFilePath, dataFileSize,
                                     self.uploadModel,
                                     ProgressCallback=Md5ProgressCallback)

            if self.uploadModel.Canceled():
                # self.foldersController.SetCanceled()
                logger.debug("Upload for \"%s\" was canceled "
                             "before it began uploading." %
                             self.uploadModel.GetRelativePathToUpload())
                return
        else:
            dataFileSize = int(self.existingUnverifiedDatafile.GetSize())

        self.uploadModel.SetProgress(0)
        self.uploadsModel.UploadProgressUpdated(self.uploadModel)
        if dataFileSize == 0:
            self.uploadsModel.UploadFileSizeUpdated(self.uploadModel)
            self.uploadModel.SetMessage("MyTardis will not accept a "
                                        "data file with a size of zero.")
            self.uploadsModel.UploadMessageUpdated(self.uploadModel)
            self.uploadModel.SetStatus(UploadStatus.FAILED)
            self.uploadsModel.UploadStatusUpdated(self.uploadModel)
            return

        if self.foldersController.IsShuttingDown():
            return
        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST or \
                not self.existingUnverifiedDatafile:
            self.uploadModel.SetMessage("Checking MIME type...")
            # mimetypes.guess_type(...) is not thread-safe!
            mimeTypes = mimetypes.MimeTypes()
            dataFileMimeType = mimeTypes.guess_type(dataFilePath)[0]

            if self.foldersController.IsShuttingDown():
                return
            self.uploadModel.SetMessage("Defining JSON data for POST...")
            datasetUri = self.folderModel.GetDatasetModel().GetResourceUri()
            dataFileCreatedTime = \
                self.folderModel.GetDataFileCreatedTime(self.dataFileIndex)
            dataFileJson = {"dataset": datasetUri,
                            "filename": dataFileName,
                            "directory": dataFileDirectory,
                            "md5sum": dataFileMd5Sum,
                            "size": dataFileSize,
                            "mimetype": dataFileMimeType,
                            "created_time": dataFileCreatedTime}

            if self.uploadModel.Canceled():
                # self.foldersController.SetCanceled()
                logger.debug("Upload for \"%s\" was canceled "
                             "before it began uploading." %
                             self.uploadModel.GetRelativePathToUpload())
                return
        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST or \
                not self.existingUnverifiedDatafile:
            self.uploadModel.SetMessage("Initializing buffered reader...")
            datafileBufferedReader = io.open(dataFilePath, 'rb')
            self.uploadModel.SetBufferedReader(datafileBufferedReader)

        def ProgressCallback(param, current, total, message=None):
            if self.uploadModel.Canceled():
                # self.foldersController.SetCanceled()
                return
            percentComplete = \
                100.0 - ((total - current) * 100.0) / total
            self.uploadModel.SetBytesUploaded(current)
            # self.uploadModel.SetProgress(float(percentComplete))
            self.uploadModel.SetProgress(int(percentComplete))
            self.uploadsModel.UploadProgressUpdated(self.uploadModel)
            if message:
                self.uploadModel.SetMessage(message)
            else:
                if total >= (1024 * 1024 * 1024):
                    self.uploadModel.SetMessage("%3.1f %%  uploaded"
                                                % percentComplete)
                else:
                    self.uploadModel.SetMessage("%3d %%  uploaded"
                                                % int(percentComplete))
            self.uploadsModel.UploadMessageUpdated(self.uploadModel)
            myTardisUrl = self.settingsModel.GetMyTardisUrl()
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.ConnectionStatusEvent(
                    myTardisUrl=myTardisUrl,
                    connectionStatus=ConnectionStatus.CONNECTED))

        # FIXME: The database interactions below should go in a model class.

        if self.foldersController.uploadMethod == UploadMethod.HTTP_POST:
            datagen, headers = poster.encode.multipart_encode(
                {"json_data": json.dumps(dataFileJson),
                 "attached_file": datafileBufferedReader},
                cb=ProgressCallback)
            opener = poster.streaminghttp.register_openers()
            opener.addheaders = [("Authorization", "ApiKey " +
                                  myTardisUsername +
                                  ":" + myTardisApiKey),
                                 ("Content-Type", "application/json"),
                                 ("Accept", "application/json")]
        elif not self.existingUnverifiedDatafile:
            headers = {"Authorization": "ApiKey " +
                       myTardisUsername + ":" + myTardisApiKey,
                       "Content-Type": "application/json",
                       "Accept": "application/json"}
            data = json.dumps(dataFileJson)

        self.uploadModel.SetMessage("Uploading...")
        postSuccess = False
        uploadSuccess = False

        request = None
        response = None
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
                    if postSuccess or self.existingUnverifiedDatafile:
                        uploadToStagingRequest = self.settingsModel\
                            .GetUploadToStagingRequest()
                        hostJson = \
                            uploadToStagingRequest['approved_staging_host']
                        host = hostJson['host']
                        username = uploadToStagingRequest['approved_username']
                        privateKeyFilePath = self.settingsModel\
                            .GetSshKeyPair().GetPrivateKeyFilePath()
                        if self.existingUnverifiedDatafile:
                            uri = self.existingUnverifiedDatafile\
                                .GetReplicas()[0].GetUri()
                        else:
                            uri = response.json()['replicas'][0]['uri']
                        while True:
                            try:
                                OpenSSH.UploadFile(dataFilePath,
                                                   dataFileSize,
                                                   username,
                                                   privateKeyFilePath,
                                                   host, uri,
                                                   ProgressCallback,
                                                   self.foldersController,
                                                   self.uploadModel)
                            except IOError, e:
                                if self.uploadModel.GetRetries() < \
                                        self.uploadModel.GetMaxRetries():
                                    self.uploadModel.IncrementRetries()
                                    logger.debug("Restarting upload for " +
                                                 dataFilePath)
                                    self.uploadModel.SetMessage(
                                        "This file will be re-uploaded...")
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
                                "account." % myTardisDefaultUsername
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
                            try:
                                message += "ERROR: \"%s\"" \
                                    % response.json()['error_message']
                            except:
                                message = "Internal Server Error: " \
                                    "See MyData's log for further " \
                                    "information."
                            raise InternalServerError(message)
                        else:
                            # FIXME: If POST fails for some other reason,
                            # for now, we will just populate the upload's
                            # message field with an error message, and
                            # allow the other uploads to continue.  There
                            # may be other critical errors where we should
                            # raise an exception and abort all uploads.
                            pass
            except DoesNotExist, e:
                # This generally means that MyTardis's API couldn't assign
                # a staging storage box, possibly because the MyTardis
                # administrator hasn't created a storage box record with
                # the correct storage box attribute, i.e.
                # (key="Staging", value=True). The staging storage box should
                # also have a storage box option with
                # (key="location", value="/mnt/.../MYTARDIS_STAGING")
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.ShutdownUploadsEvent(
                        failed=True))
                message = str(e)
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController
                        .ShowMessageDialogEvent(
                            title="MyData",
                            message=message,
                            icon=wx.ICON_ERROR))
                return
            except StagingHostRefusedSshConnection, e:
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.ShutdownUploadsEvent(
                        failed=True))
                message = str(e)
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController
                        .ShowMessageDialogEvent(
                            title="MyData",
                            message=message,
                            icon=wx.ICON_ERROR))
                return
            except StagingHostSshPermissionDenied, e:
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.ShutdownUploadsEvent(
                        failed=True))
                message = str(e)
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController
                        .ShowMessageDialogEvent(
                            title="MyData",
                            message=message,
                            icon=wx.ICON_ERROR))
                return
            except ScpException, e:
                if self.foldersController.IsShuttingDown() or \
                        self.uploadModel.Canceled():
                    return
                message = str(e)
                message += "\n\n" + e.command
                logger.error(message)
            except ValueError, e:
                if str(e) == "read of closed file" or \
                        str(e) == "seek of closed file":
                    logger.debug("Aborting upload for \"%s\" because "
                                 "file handle was closed." %
                                 self.uploadModel.GetRelativePathToUpload())
                    return
                else:
                    raise
        except urllib2.HTTPError, e:
            logger.error("url: " + url)
            logger.error(traceback.format_exc())
            errorResponse = e.read()
            logger.error(errorResponse)
            wx.PostEvent(
                self.foldersController.notifyWindow,
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
                message += str(e)
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController
                    .ShowMessageDialogEvent(
                        title="MyData",
                        message=message,
                        icon=wx.ICON_ERROR))
            return
        except Exception, e:
            if not self.foldersController.IsShuttingDown():
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.ConnectionStatusEvent(
                        myTardisUrl=self.settingsModel.GetMyTardisUrl(),
                        connectionStatus=ConnectionStatus.DISCONNECTED))

            self.uploadModel.SetMessage(str(e))
            self.uploadsModel.UploadMessageUpdated(self.uploadModel)
            self.uploadModel.SetStatus(UploadStatus.FAILED)
            self.uploadsModel.UploadStatusUpdated(self.uploadModel)
            if dataFileDirectory != "":
                logger.debug("Upload failed for datafile " + dataFileName +
                             " in subdirectory " + dataFileDirectory +
                             " of folder " + self.folderModel.GetFolder())
            else:
                logger.debug("Upload failed for datafile " + dataFileName +
                             " in folder " + self.folderModel.GetFolder())
            if not self.existingUnverifiedDatafile:
                logger.debug(url)
                if hasattr(e, "code"):
                    logger.error(e.code)
                logger.error(str(e))
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
                if hasattr(e, "headers"):
                    logger.debug(str(e.headers))
                if hasattr(response, "headers"):
                    # logger.debug(str(response.headers))
                    pass
            logger.debug(traceback.format_exc())
            return

        if uploadSuccess:
            logger.debug("Upload succeeded for " + dataFilePath)
            self.uploadModel.SetStatus(UploadStatus.COMPLETED)
            self.uploadsModel.UploadStatusUpdated(self.uploadModel)
            self.uploadModel.SetMessage("Upload complete!")
            # self.uploadModel.SetProgress(100.0)
            self.uploadModel.SetProgress(100)
            self.uploadsModel.UploadProgressUpdated(self.uploadModel)
            self.folderModel.SetDataFileUploaded(self.dataFileIndex,
                                                 uploaded=True)
            self.foldersModel.FolderStatusUpdated(self.folderModel)
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.UploadCompleteEvent(
                    id=self.foldersController.EVT_UPLOAD_COMPLETE,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    uploadModel=self.uploadModel))
        else:
            if self.foldersController.IsShuttingDown() or \
                    self.uploadModel.Canceled():
                return
            logger.error("Upload failed for " + dataFilePath)
            self.uploadModel.SetStatus(UploadStatus.FAILED)
            self.uploadsModel.UploadStatusUpdated(self.uploadModel)
            if not postSuccess and response is not None:
                message = "Internal Server Error: " \
                    "See MyData's log for further " \
                    "information."
                logger.error(message)
                self.uploadModel.SetMessage(response.text)
            else:
                self.uploadModel.SetMessage("Upload failed.")

            # self.uploadModel.SetProgress(0.0)
            self.uploadModel.SetProgress(0)
            self.uploadsModel.UploadProgressUpdated(self.uploadModel)
            self.folderModel.SetDataFileUploaded(self.dataFileIndex,
                                                 uploaded=False)
            self.foldersModel.FolderStatusUpdated(self.folderModel)
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.UploadCompleteEvent(
                    id=self.foldersController.EVT_UPLOAD_COMPLETE,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex,
                    uploadModel=self.uploadModel))

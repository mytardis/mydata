"""
The main controller class for managing datafile verifications
and uploads from each of the folders in the Folders view.
"""

# pylint: disable=missing-docstring

import os
import sys
import threading
import requests
import Queue
import traceback
import subprocess
import hashlib

from mydata.utils.openssh import OPENSSH
from mydata.utils import ConnectionStatus

from mydata.models.experiment import ExperimentModel
from mydata.models.dataset import DatasetModel
from mydata.controllers.uploads import UploadMethod
from mydata.controllers.uploads import UploadDatafileRunnable
from mydata.controllers.verifications import VerifyDatafileRunnable

from mydata.logs import logger

import wx
import wx.lib.newevent
import wx.dataview


class FoldersController(object):
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    """
    The main controller class for managing datafile verifications
    and uploads from each of the folders in the Folders view.
    """
    def __init__(self, notifyWindow, foldersModel, foldersView, usersModel,
                 verificationsModel, uploadsModel, settingsModel):
        # pylint: disable=too-many-arguments
        self.notifyWindow = notifyWindow
        self.foldersModel = foldersModel
        self.foldersView = foldersView
        self.usersModel = usersModel
        self.verificationsModel = verificationsModel
        self.uploadsModel = uploadsModel
        self.settingsModel = settingsModel

        self.shuttingDown = threading.Event()
        self.showingErrorDialog = threading.Event()
        self.lastErrorMessage = None
        self.showingWarningDialog = threading.Event()
        self.canceled = threading.Event()
        self.failed = threading.Event()

        self.finishedCountingVerifications = False
        self.verificationsQueue = None
        self.threadingLock = threading.Lock()
        self.uploadsThreadingLock = threading.Lock()
        self.verifyDatafileRunnable = None
        self.uploadsQueue = None
        self.started = False
        self.completed = False
        self.uploadDatafileRunnable = None
        self.numVerificationsToBePerformed = 0
        self.uploadMethod = UploadMethod.HTTP_POST

        # These will get overwritten in StartDataUploads, but we need
        # to initialize them here, so that ShutDownUploadThreads()
        # can be called.
        self.numVerificationWorkerThreads = 0
        self.verificationWorkerThreads = []
        self.numUploadWorkerThreads = 0
        self.uploadWorkerThreads = []

        self.foldersView.Bind(wx.EVT_BUTTON, self.OnOpenFolder,
                              self.foldersView.GetOpenFolderButton())
        self.foldersView.GetDataViewControl()\
            .Bind(wx.dataview.EVT_DATAVIEW_ITEM_ACTIVATED, self.OnOpenFolder)

        self.didntFindDatafileOnServerEvent, eventBinder = \
            wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(eventBinder, self.UploadDatafile)

        self.unverifiedDatafileOnServerEvent, eventBinder = \
            wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(eventBinder, self.UploadDatafile)

        self.connectionStatusEvent, eventBinder = wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(eventBinder, self.UpdateStatusBar)

        self.showMessageDialogEvent, eventBinder = \
            wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(eventBinder, self.ShowMessageDialog)

        self.shutdownUploadsEvent, eventBinder = wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(eventBinder, self.ShutDownUploadThreads)

        self.foundVerifiedDatafileEvent, eventBinder = \
            wx.lib.newevent.NewCommandEvent()
        self.EVT_FOUND_VERIFIED_DATAFILE = wx.NewId()  # pylint: disable=invalid-name
        self.notifyWindow.Bind(eventBinder,
                               self.CountCompletedUploadsAndVerifications)

        self.foundUnverifiedDatafileEvent, eventBinder = \
            wx.lib.newevent.NewCommandEvent()
        self.EVT_FOUND_UNVERIFIED_BUT_FULL_SIZE_DATAFILE = wx.NewId()  # pylint:disable=invalid-name
        self.notifyWindow.Bind(eventBinder,
                               self.CountCompletedUploadsAndVerifications)

        self.uploadCompleteEvent, eventBinder = \
            wx.lib.newevent.NewCommandEvent()
        self.EVT_UPLOAD_COMPLETE = wx.NewId()  # pylint:disable=invalid-name
        self.notifyWindow.Bind(eventBinder,
                               self.CountCompletedUploadsAndVerifications)

    def Started(self):
        return self.started

    def SetStarted(self, started=True):
        self.started = started

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

    def GetLastErrorMessage(self):
        return self.lastErrorMessage

    def SetLastErrorMessage(self, message):
        self.threadingLock.acquire()
        self.lastErrorMessage = message
        self.threadingLock.release()

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
        elif event.message == self.GetLastErrorMessage():
            # Sometimes multiple threads can encounter the same exception
            # at around the same time.  The first thread's exception leads
            # to a modal error dialog, which blocks the events queue, so
            # the next thread's (identical) show message dialog event doesn't
            # get caught until after the first message dialog has been closed.
            # In this case, the above check (to prevent two error dialogs
            # from appearing at the same time) doesn't help.
            logger.warning("Refusing to show message dialog for message "
                           "\"%s\" because we already showed an error "
                           "dialog with the same message." % event.message)
            return
        self.SetLastErrorMessage(event.message)
        if event.icon == wx.ICON_ERROR:
            self.SetShowingErrorDialog(True)
        dlg = wx.MessageDialog(None, event.message, event.title,
                               wx.OK | event.icon)
        # pylint: disable=bare-except
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
        Called in response to didntFindDatafileOnServerEvent or
        unverifiedDatafileOnServerEvent.

        This method runs in the main thread, so it shouldn't do anything
        time-consuming or blocking, unless it launches another thread.
        Because this method adds upload tasks to a queue, it is important
        to note that if the queue has a maxsize set, then an attempt to
        add something to the queue could block the GUI thread, making the
        application appear unresponsive.
        """
        folderModel = event.folderModel
        dfi = event.dataFileIndex

        if folderModel not in self.uploadDatafileRunnable:
            self.uploadDatafileRunnable[folderModel] = {}

        existingUnverifiedDatafile = \
            getattr(event, "existingUnverifiedDatafile", False)
        bytesUploadedPreviously = getattr(event, "bytesUploadedToStaging", 0)
        verificationModel = getattr(event, "verificationModel", None)
        self.uploadDatafileRunnable[folderModel][dfi] = \
            UploadDatafileRunnable(self, self.foldersModel, folderModel,
                                   dfi, self.uploadsModel,
                                   self.settingsModel,
                                   existingUnverifiedDatafile,
                                   verificationModel,
                                   bytesUploadedPreviously)
        self.uploadsQueue.put(self.uploadDatafileRunnable[folderModel][dfi])

    def StartDataUploads(self):
        # pylint: disable=too-many-return-statements
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        fc = self  # pylint: disable=invalid-name
        fc.SetStarted()
        settingsModel = fc.settingsModel
        fc.canceled.clear()
        fc.verificationsModel.DeleteAllRows()
        fc.uploadsModel.DeleteAllRows()
        fc.verifyDatafileRunnable = {}
        fc.verificationsQueue = Queue.Queue()
        # For now, the max number of verification threads is set to be the
        # same as the max number of upload threads.
        fc.numVerificationWorkerThreads = settingsModel.GetMaxUploadThreads()
        fc.verificationWorkerThreads = []

        for i in range(fc.numVerificationWorkerThreads):
            thread = threading.Thread(name="VerificationWorkerThread-%d" % (i + 1),
                                      target=fc.VerificationWorker)
            fc.verificationWorkerThreads.append(thread)
            thread.start()
        fc.uploadDatafileRunnable = {}
        fc.uploadsQueue = Queue.Queue()
        fc.numUploadWorkerThreads = settingsModel.GetMaxUploadThreads()
        fc.uploadMethod = UploadMethod.HTTP_POST

        # pylint: disable=broad-except
        try:
            settingsModel.GetUploaderModel().RequestStagingAccess()
            uploadToStagingRequest = settingsModel\
                .GetUploadToStagingRequest()
        except Exception, err:
            # MyData app could be missing from MyTardis server.
            logger.error(traceback.format_exc())
            wx.PostEvent(
                self.notifyWindow,
                self.showMessageDialogEvent(
                    title="MyData",
                    message=str(err),
                    icon=wx.ICON_ERROR))
            return
        message = None
        if uploadToStagingRequest is None:
            message = "Couldn't determine whether uploads to " \
                      "staging have been approved.  " \
                      "Falling back to HTTP POST."
        elif uploadToStagingRequest.IsApproved():
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
                self.showMessageDialogEvent(
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
            thread = threading.Thread(name="UploadWorkerThread-%d" % (i + 1),
                                      target=fc.UploadWorker, args=())
            fc.uploadWorkerThreads.append(thread)
            thread.start()
        # pylint: disable=bare-except
        try:
            fc.numVerificationsToBePerformed = 0
            fc.finishedCountingVerifications = \
                threading.Event()
            for row in range(0, self.foldersModel.GetRowCount()):
                if self.IsShuttingDown():
                    return
                folderModel = self.foldersModel.GetFolderRecord(row)
                fc.numVerificationsToBePerformed += folderModel.GetNumFiles()
                logger.debug(
                    "StartDataUploads: Starting verifications "
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
                    # pylint: disable=broad-except
                    try:
                        experimentModel = ExperimentModel\
                            .GetOrCreateExperimentForFolder(folderModel)
                    except Exception, err:
                        logger.error(traceback.format_exc())
                        wx.PostEvent(
                            self.notifyWindow,
                            self.showMessageDialogEvent(
                                title="MyData",
                                message=str(err),
                                icon=wx.ICON_ERROR))
                        return
                    folderModel.SetExperiment(experimentModel)
                    connected = ConnectionStatus.CONNECTED
                    wx.PostEvent(
                        self.notifyWindow,
                        self.connectionStatusEvent(
                            myTardisUrl=myTardisUrl,
                            connectionStatus=connected))
                    # pylint: disable=broad-except
                    try:
                        datasetModel = DatasetModel\
                            .CreateDatasetIfNecessary(folderModel)
                    except Exception, err:
                        logger.error(traceback.format_exc())
                        wx.PostEvent(
                            self.notifyWindow,
                            self.showMessageDialogEvent(
                                title="MyData",
                                message=str(err),
                                icon=wx.ICON_ERROR))
                        return
                    folderModel.SetDatasetModel(datasetModel)
                    self.VerifyDatafiles(folderModel)
                except requests.exceptions.ConnectionError, err:
                    if not self.IsShuttingDown():
                        disconnected = \
                            ConnectionStatus.DISCONNECTED
                        wx.PostEvent(
                            self.notifyWindow,
                            self.connectionStatusEvent(
                                myTardisUrl=myTardisUrl,
                                connectionStatus=disconnected))
                    return
                except ValueError, err:
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
            fc.finishedCountingVerifications.set()
            # End: for row in range(0, self.foldersModel.GetRowCount())
        except:
            logger.error(traceback.format_exc())

    def UploadWorker(self):
        # pylint: disable=fixme
        # FIXME: Should this be in uploads (not folders) controller?
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
                return
            # pylint: disable=bare-except
            try:
                task.Run()
            except ValueError, err:
                if str(err) == "I/O operation on closed file":
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

    def VerificationWorker(self):
        # pylint: disable=fixme
        # FIXME: Should this be in verifications (not folders) controller?
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
            # pylint: disable=bare-except
            try:
                task.Run()
            except ValueError, err:
                if str(err) == "I/O operation on closed file":
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
        # pylint: disable=unused-argument
        numVerificationsCompleted = self.verificationsModel.GetCompletedCount()

        uploadsToBePerformed = self.uploadsModel.GetRowCount()
        uploadsCompleted = self.uploadsModel.GetCompletedCount()
        uploadsFailed = self.uploadsModel.GetFailedCount()
        uploadsProcessed = uploadsCompleted + uploadsFailed

        if numVerificationsCompleted == self.numVerificationsToBePerformed \
                and self.finishedCountingVerifications.isSet() \
                and uploadsProcessed == uploadsToBePerformed:
            logger.debug("All datafile verifications and uploads "
                         "have completed.")
            logger.debug("Shutting down upload and verification threads.")
            wx.PostEvent(self.notifyWindow,
                         self.shutdownUploadsEvent(completed=True))

    def ShutDownUploadThreads(self, event=None):
        # pylint: disable=too-many-branches
        if self.IsShuttingDown():
            return
        self.SetShuttingDown(True)
        message = "Shutting down upload threads..."
        logger.info(message)
        if hasattr(wx.GetApp(), "GetMainFrame"):
            wx.GetApp().GetMainFrame().SetStatusMessage(message)
        if hasattr(event, "failed") and event.failed:
            self.SetFailed()
            self.uploadsModel.CancelRemaining()
        elif hasattr(event, "completed") and event.completed:
            self.SetCompleted()
        else:
            self.SetCanceled()
        logger.debug("Shutting down FoldersController upload worker threads.")
        for _ in range(self.numUploadWorkerThreads):
            self.uploadsQueue.put(None)
        for thread in self.uploadWorkerThreads:
            thread.join()
        logger.debug("Shutting down FoldersController verification "
                     "worker threads.")
        for _ in range(self.numVerificationWorkerThreads):
            self.verificationsQueue.put(None)
        for thread in self.verificationWorkerThreads:
            thread.join()

        self.verifyDatafileRunnable = {}
        self.uploadDatafileRunnable = {}

        if sys.platform == 'darwin':
            sshControlMasterPool = \
                OPENSSH.GetSshControlMasterPool(createIfMissing=False)
            if sshControlMasterPool:
                sshControlMasterPool.ShutDown()

        if self.Failed():
            message = "Data scans and uploads failed."
        elif self.Canceled():
            message = "Data scans and uploads were canceled."
        elif self.uploadsModel.GetFailedCount() > 0:
            message = \
                "Data scans and uploads completed with " \
                "%d failed upload(s)." % self.uploadsModel.GetFailedCount()
        elif self.Completed():
            message = "Data scans and uploads completed successfully."
        else:
            message = "Data scans and uploads appear to have " \
                "completed successfully."
        logger.info(message)
        if hasattr(wx.GetApp(), "GetMainFrame"):
            wx.GetApp().GetMainFrame().SetStatusMessage(message)
        app = wx.GetApp()
        if hasattr(app, "toolbar"):
            app.toolbar.EnableTool(app.stopTool.GetId(), False)
        if hasattr(wx.GetApp(), "SetPerformingLookupsAndUploads"):
            wx.GetApp().SetPerformingLookupsAndUploads(False)
        self.SetShuttingDown(False)

        # pylint: disable=bare-except
        try:
            wx.EndBusyCursor()
        except:
            pass

        logger.debug("")

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

    # pylint: disable=unused-argument
    def OnOpenFolder(self, event):
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
            def OpenFolder(path):
                """Open folder."""
                subprocess.check_call(['open', '--', path])
        elif sys.platform.startswith('linux'):
            def OpenFolder(path):
                """Open folder."""
                subprocess.check_call(['xdg-open', '--', path])
        elif sys.platform.startswith('win'):
            def OpenFolder(path):
                """Open folder."""
                subprocess.call(['explorer', path])
        else:
            logger.debug("sys.platform = " + sys.platform)

        OpenFolder(path)

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
                if self.IsShuttingDown() or uploadModel.Canceled():
                    logger.debug("Aborting MD5 calculation for "
                                 "%s" % filePath)
                    return None
                md5.update(chunk)
                bytesProcessed += len(chunk)
                del chunk
                if progressCallback:
                    progressCallback(bytesProcessed)
        return md5.hexdigest()

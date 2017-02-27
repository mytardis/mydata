"""
The main controller class for managing datafile verifications
and uploads from each of the folders in the Folders view.
"""

# pylint: disable=missing-docstring

import sys
import time
import threading
# For Python3, this will change to "from queue import Queue":
from Queue import Queue
import traceback
import datetime

import requests

import wx
import wx.lib.newevent
import wx.dataview

import mydata.events as mde
from ..models.experiment import ExperimentModel
from ..models.dataset import DatasetModel
from ..logs import logger
from ..utils import BeginBusyCursorIfRequired
from ..utils import EndBusyCursorIfRequired
from ..utils.openssh import CleanUpSshProcesses
from .uploads import UploadMethod
from .uploads import UploadDatafileRunnable
from .verifications import VerifyDatafileRunnable

if sys.platform.startswith("linux"):
    from ..linuxsubprocesses import RestartErrandBoy


class FoldersController(object):
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-statements
    """
    The main controller class for managing datafile verifications
    and uploads from each of the folders in the Folders view.
    """
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
        self.lastErrorMessage = None
        self.showingWarningDialog = threading.Event()
        self.canceled = threading.Event()
        self.failed = threading.Event()
        self.started = threading.Event()
        self.completed = threading.Event()

        self.finishedCountingVerifications = dict()
        self.finishedCountingThreadingLock = threading.Lock()
        self.finishedScanningForDatasetFolders = threading.Event()
        self.verificationsQueue = None
        self.lastErrorMessageThreadingLock = threading.Lock()
        self.getOrCreateExpThreadingLock = threading.Lock()
        self.verifyDatafileRunnable = None
        self.uploadsQueue = None
        self.uploadDatafileRunnable = None
        self.numVerificationsToBePerformed = 0
        self.numVerificationsToBePerformedLock = threading.Lock()
        self.uploadsAcknowledged = 0
        self.uploadMethod = UploadMethod.HTTP_POST

        # These will get overwritten in InitForUploads, but we need
        # to initialize them here, so that ShutDownUploadThreads()
        # can be called.
        self.numVerificationWorkerThreads = 0
        self.verificationWorkerThreads = []
        self.numUploadWorkerThreads = 0
        self.uploadWorkerThreads = []

        self.testRun = False

        # pylint: disable=invalid-name
        self.DidntFindDatafileOnServerEvent, \
            self.EVT_DIDNT_FIND_FILE_ON_SERVER, _ = \
            mde.NewEvent(self.notifyWindow, self.UploadDatafile)
        self.UnverifiedDatafileOnServerEvent, \
            self.EVT_UNVERIFIED_DATAFILE_ON_SERVER, _ = \
            mde.NewEvent(self.notifyWindow, self.UploadDatafile)
        self.ShowMessageDialogEvent, \
            self.EVT_SHOW_MESSAGE_DIALOG, _ = \
            mde.NewEvent(self.notifyWindow, self.ShowMessageDialog)
        self.ShutdownUploadsEvent, \
            self.EVT_SHUTDOWN_UPLOADS, _ = \
            mde.NewEvent(self.notifyWindow, self.ShutDownUploadThreads)
        self.FoundVerifiedDatafileEvent, \
            self.EVT_FOUND_VERIFIED_DATAFILE, _ = \
            mde.NewEvent(self.notifyWindow,
                         self.CountCompletedUploadsAndVerifications)
        self.FoundUnverifiedDatafileEvent, \
            self.EVT_FOUND_UNVERIFIED_DATAFILE, _ = \
            mde.NewEvent(self.notifyWindow,
                         self.CountCompletedUploadsAndVerifications)
        self.FoundUnverifiedNoDfosDatafileEvent, \
            self.EVT_FOUND_UNVERIFIED_NO_DFOS, _ = \
            mde.NewEvent(self.notifyWindow,
                         self.CountCompletedUploadsAndVerifications)
        self.UploadCompleteEvent, \
            self.EVT_UPLOAD_COMPLETE, _ = \
            mde.NewEvent(self.notifyWindow,
                         self.CountCompletedUploadsAndVerifications)
        self.UploadFailedEvent, \
            self.EVT_UPLOAD_FAILED, _ = \
            mde.NewEvent(self.notifyWindow,
                         self.CountCompletedUploadsAndVerifications)

    def Started(self):
        return self.started.isSet()

    def SetStarted(self, started=True):
        if started:
            self.started.set()
        else:
            self.started.clear()

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
        return self.completed.isSet()

    def SetCompleted(self, completed=True):
        if completed:
            self.completed.set()
        else:
            self.completed.clear()

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
        self.lastErrorMessageThreadingLock.acquire()
        self.lastErrorMessage = message
        self.lastErrorMessageThreadingLock.release()

    def ShowMessageDialog(self, event):
        """
        Display a message dialog.

        Sometimes multiple threads can encounter the same exception
        at around the same time.  The first thread's exception leads
        to a modal error dialog, which blocks the events queue, so
        the next thread's (identical) show message dialog event doesn't
        get caught until after the first message dialog has been closed.
        In this case, we check if we already showed an error dialog with
        the same message.
        """
        if self.IsShowingErrorDialog():
            logger.warning("Refusing to show message dialog for message "
                           "\"%s\" because we are already showing an error "
                           "dialog." % event.message)
            return
        elif event.message == self.GetLastErrorMessage():
            logger.warning("Refusing to show message dialog for message "
                           "\"%s\" because we already showed an error "
                           "dialog with the same message." % event.message)
            return
        self.SetLastErrorMessage(event.message)
        if event.icon == wx.ICON_ERROR:
            self.SetShowingErrorDialog(True)
        dlg = wx.MessageDialog(None, event.message, event.title,
                               wx.OK | event.icon)
        try:
            wx.EndBusyCursor()
            needToRestartBusyCursor = True
        except:
            needToRestartBusyCursor = False
        if wx.PyApp.IsMainLoopRunning():
            dlg.ShowModal()
        else:
            sys.stderr.write("%s\n" % event.message)
        if needToRestartBusyCursor and not self.IsShuttingDown() \
                and wx.GetApp().PerformingLookupsAndUploads():
            BeginBusyCursorIfRequired()
        if event.icon == wx.ICON_ERROR:
            self.SetShowingErrorDialog(False)

    def UploadDatafile(self, event):
        """
        Called in response to DidntFindDatafileOnServerEvent or
        UnverifiedDatafileOnServerEvent.

        This method runs in the main thread, so it shouldn't do anything
        time-consuming or blocking, unless it launches another thread.
        Because this method adds upload tasks to a queue, it is important
        to note that if the queue has a maxsize set, then an attempt to
        add something to the queue could block the GUI thread, making the
        application appear unresponsive.
        """
        folderModel = event.folderModel
        dfi = event.dataFileIndex
        existingUnverifiedDatafile = \
            getattr(event, "existingUnverifiedDatafile", False)

        if self.testRun:
            if existingUnverifiedDatafile:
                message = "NEEDS RE-UPLOADING: %s" \
                    % folderModel.GetDataFileRelPath(dfi)
            else:
                message = "NEEDS UPLOADING: %s" \
                    % folderModel.GetDataFileRelPath(dfi)
            self.uploadsAcknowledged += 1
            logger.testrun(message)
            self.CountCompletedUploadsAndVerifications(event=None)
            return

        if folderModel not in self.uploadDatafileRunnable:
            self.uploadDatafileRunnable[folderModel] = {}

        bytesUploadedPreviously = \
            getattr(event, "bytesUploadedPreviously", None)
        verificationModel = getattr(event, "verificationModel", None)
        self.uploadDatafileRunnable[folderModel][dfi] = \
            UploadDatafileRunnable(self, self.foldersModel, folderModel,
                                   dfi, self.uploadsModel,
                                   self.settingsModel,
                                   existingUnverifiedDatafile,
                                   verificationModel,
                                   bytesUploadedPreviously)
        if wx.PyApp.IsMainLoopRunning():
            self.uploadsQueue.put(
                self.uploadDatafileRunnable[folderModel][dfi])
        else:
            self.uploadDatafileRunnable[folderModel][dfi].Run()
        self.CountCompletedUploadsAndVerifications(event=None)

    def InitForUploads(self):
        # pylint: disable=too-many-branches
        fc = self  # pylint: disable=invalid-name
        app = wx.GetApp()
        if hasattr(app, "TestRunRunning"):
            fc.testRun = app.TestRunRunning()
        else:
            fc.testRun = False
        fc.SetStarted()
        settingsModel = fc.settingsModel
        fc.SetCanceled(False)
        fc.SetFailed(False)
        fc.SetCompleted(False)
        fc.verificationsModel.DeleteAllRows()
        fc.uploadsModel.DeleteAllRows()
        fc.uploadsModel.SetStartTime(datetime.datetime.now())
        fc.verifyDatafileRunnable = {}
        fc.verificationsQueue = Queue()
        fc.numVerificationWorkerThreads = \
            settingsModel.miscellaneous.maxVerificationThreads
        fc.verificationWorkerThreads = []

        if wx.PyApp.IsMainLoopRunning():
            for i in range(fc.numVerificationWorkerThreads):
                thread = threading.Thread(
                    name="VerificationWorkerThread-%d" % (i + 1),
                    target=fc.VerificationWorker)
                fc.verificationWorkerThreads.append(thread)
                thread.start()
        fc.uploadDatafileRunnable = {}
        fc.uploadsQueue = Queue()
        fc.numUploadWorkerThreads = settingsModel.advanced.maxUploadThreads
        fc.uploadMethod = UploadMethod.HTTP_POST
        fc.getOrCreateExpThreadingLock = threading.Lock()

        if sys.platform.startswith("linux"):
            RestartErrandBoy()

        try:
            settingsModel.uploaderModel.RequestStagingAccess()
            uploadToStagingRequest = settingsModel.uploadToStagingRequest
        except Exception as err:
            # MyData app could be missing from MyTardis server.
            logger.error(traceback.format_exc())
            mde.PostEvent(
                self.ShowMessageDialogEvent(
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
            mde.PostEvent(
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
        if wx.PyApp.IsMainLoopRunning():
            for i in range(fc.numUploadWorkerThreads):
                thread = threading.Thread(
                    name="UploadWorkerThread-%d" % (i + 1),
                    target=fc.UploadWorker, args=())
                fc.uploadWorkerThreads.append(thread)
                thread.start()

        fc.finishedScanningForDatasetFolders = threading.Event()
        fc.numVerificationsToBePerformed = 0
        fc.finishedCountingVerifications = dict()

    def FinishedScanningForDatasetFolders(self):
        """
        At this point, we know that FoldersModel's
        ScanFolders method has finished populating
        self.foldersModel with dataset folders.
        """
        self.finishedScanningForDatasetFolders.set()
        logger.debug("Finished scanning for dataset folders.")
        while len(self.finishedCountingVerifications.keys()) < \
                self.foldersModel.GetCount():
            time.sleep(0.01)
        self.CountCompletedUploadsAndVerifications(event=None)

    def StartUploadsForFolder(self, folderModel):
        # pylint: disable=too-many-return-statements
        # pylint: disable=too-many-branches
        fc = self  # pylint: disable=invalid-name
        try:
            self.finishedCountingThreadingLock.acquire()
            fc.finishedCountingVerifications[folderModel] = threading.Event()
            self.finishedCountingThreadingLock.release()
            app = wx.GetApp()
            if self.IsShuttingDown() or \
                    (hasattr(app, "ShouldAbort") and app.ShouldAbort()):
                return
            fc.numVerificationsToBePerformedLock.acquire()
            fc.numVerificationsToBePerformed += folderModel.GetNumFiles()
            fc.numVerificationsToBePerformedLock.release()
            logger.debug(
                "StartUploadsForFolder: Starting verifications "
                "and uploads for folder: " +
                folderModel.GetFolder())
            if self.IsShuttingDown() or \
                    (hasattr(app, "ShouldAbort") and app.ShouldAbort()):
                return
            try:
                try:
                    self.getOrCreateExpThreadingLock.acquire()
                    experimentModel = ExperimentModel\
                        .GetOrCreateExperimentForFolder(folderModel,
                                                        fc.testRun)
                except Exception as err:
                    logger.error(traceback.format_exc())
                    mde.PostEvent(
                        self.ShowMessageDialogEvent(
                            title="MyData",
                            message=str(err),
                            icon=wx.ICON_ERROR))
                    return
                finally:
                    self.getOrCreateExpThreadingLock.release()
                folderModel.SetExperiment(experimentModel)
                try:
                    datasetModel = DatasetModel\
                        .CreateDatasetIfNecessary(folderModel, fc.testRun)
                except Exception as err:
                    logger.error(traceback.format_exc())
                    mde.PostEvent(
                        self.ShowMessageDialogEvent(
                            title="MyData",
                            message=str(err),
                            icon=wx.ICON_ERROR))
                    return
                folderModel.SetDatasetModel(datasetModel)
                self.VerifyDatafiles(folderModel)
            except requests.exceptions.ConnectionError as err:
                logger.error(str(err))
                return
            except ValueError:
                logger.error("Failed to retrieve experiment "
                             "for folder " +
                             str(folderModel.GetFolder()))
                logger.error(traceback.format_exc())
                return
            if experimentModel is None and not fc.testRun:
                logger.error("Failed to acquire a MyTardis "
                             "experiment to store data in for "
                             "folder " +
                             folderModel.GetFolder())
                return
            if self.IsShuttingDown() or \
                    (hasattr(app, "ShouldAbort") and app.ShouldAbort()):
                return
            self.finishedCountingThreadingLock.acquire()
            fc.finishedCountingVerifications[folderModel].set()
            self.finishedCountingThreadingLock.release()
            if self.foldersModel.GetRowCount() == 0 or \
                    fc.numVerificationsToBePerformed == 0:
                # For the case of zero folders or zero files, we
                # can't use the usual triggers (e.g. datafile
                # upload complete) to determine when to check if
                # we have finished:
                self.CountCompletedUploadsAndVerifications(event=None)
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
            try:
                task.Run()
            except ValueError as err:
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
            try:
                task.Run()
            except ValueError as err:
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
        if self.Completed() or self.Canceled():
            return

        numVerificationsCompleted = self.verificationsModel.GetCompletedCount()

        uploadsToBePerformed = self.uploadsModel.GetRowCount() + \
            self.uploadsQueue.qsize()

        uploadsCompleted = self.uploadsModel.GetCompletedCount()
        uploadsFailed = self.uploadsModel.GetFailedCount()
        uploadsProcessed = uploadsCompleted + uploadsFailed

        if hasattr(wx.GetApp(), "GetMainFrame"):
            if numVerificationsCompleted == \
                    self.numVerificationsToBePerformed \
                    and uploadsToBePerformed > 0:
                message = "Uploaded %d of %d files." % \
                    (uploadsCompleted, uploadsToBePerformed)
            else:
                message = "Looked up %d of %d files on server." % \
                    (numVerificationsCompleted,
                     self.numVerificationsToBePerformed)
            wx.GetApp().GetMainFrame().SetStatusMessage(message)

        finishedVerificationCounting = \
            self.finishedScanningForDatasetFolders.isSet()
        for folder in self.finishedCountingVerifications:
            if not self.finishedCountingVerifications[folder]:
                finishedVerificationCounting = False
                break

        if numVerificationsCompleted == self.numVerificationsToBePerformed \
                and finishedVerificationCounting \
                and (uploadsProcessed == uploadsToBePerformed or
                     self.testRun and
                     self.uploadsAcknowledged == uploadsToBePerformed):
            logger.debug("All datafile verifications and uploads "
                         "have completed.")
            logger.debug("Shutting down upload and verification threads.")
            mde.PostEvent(self.ShutdownUploadsEvent(completed=True))
        elif not wx.PyApp.IsMainLoopRunning() and self.testRun and \
                finishedVerificationCounting:
            mde.PostEvent(self.ShutdownUploadsEvent(completed=True))

    def ShutDownUploadThreads(self, event=None):
        # pylint: disable=too-many-branches
        if self.IsShuttingDown():
            return
        if hasattr(wx.GetApp(), "SetPerformingLookupsAndUploads"):
            if not wx.GetApp().PerformingLookupsAndUploads():
                EndBusyCursorIfRequired()
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
            self.uploadsModel.CancelRemaining()
        logger.debug("Shutting down FoldersController upload worker threads.")
        for _ in range(self.numUploadWorkerThreads):
            self.uploadsQueue.put(None)
        if self.uploadMethod == UploadMethod.VIA_STAGING:
            # SCP can leave orphaned SSH processes which need to be
            # cleaned up.
            CleanUpSshProcesses(self.settingsModel)
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

        if self.testRun:
            numVerificationsCompleted = \
                self.verificationsModel.GetCompletedCount()
            numVerifiedUploads = \
                self.verificationsModel.GetFoundVerifiedCount()
            numFilesNotFoundOnServer = \
                self.verificationsModel.GetNotFoundCount()
            numFullSizeUnverifiedUploads = \
                self.verificationsModel.GetFoundUnverifiedFullSizeCount()
            numIncompleteUploads = \
                self.verificationsModel.GetFoundUnverifiedNotFullSizeCount()
            numFailedLookups = self.verificationsModel.GetFailedCount()
            logger.testrun("")
            logger.testrun("SUMMARY")
            logger.testrun("")
            logger.testrun("Files looked up on server: %s"
                           % numVerificationsCompleted)
            logger.testrun("Files verified on server: %s" % numVerifiedUploads)
            logger.testrun("Files not found on server: %s"
                           % numFilesNotFoundOnServer)
            logger.testrun("Files unverified (but full size) on server: %s"
                           % numFullSizeUnverifiedUploads)
            logger.testrun("Files unverified (and incomplete) on server: %s"
                           % numIncompleteUploads)
            logger.testrun("Failed lookups: %s" % numFailedLookups)
            logger.testrun("")

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
            if self.uploadsModel.GetCompletedCount() > 0:
                elapsedTime = self.uploadsModel.GetElapsedTime()
                if elapsedTime and not self.testRun:
                    averageSpeedMBs = \
                        (float(self.uploadsModel.GetCompletedSize()) /
                         1000000.0 / elapsedTime.total_seconds())
                    if averageSpeedMBs >= 1.0:
                        averageSpeed = "%3.1f MB/s" % averageSpeedMBs
                    else:
                        averageSpeed = \
                            "%3.1f KB/s" % (averageSpeedMBs * 1000.0)
                    message += "  Average speed: %s" % averageSpeed
        else:
            message = "Data scans and uploads appear to have " \
                "completed successfully."
        logger.info(message)
        if hasattr(wx.GetApp(), "GetMainFrame"):
            wx.GetApp().GetMainFrame().SetStatusMessage(message)
        if self.testRun:
            logger.testrun(message)

        app = wx.GetApp()
        if hasattr(app, "toolbar"):
            app.EnableTestAndUploadToolbarButtons()
            app.SetShouldAbort(False)
            if self.testRun:
                app.testRunFrame.saveButton.Enable()
        if hasattr(wx.GetApp(), "SetPerformingLookupsAndUploads"):
            wx.GetApp().SetPerformingLookupsAndUploads(False)
        self.SetShuttingDown(False)
        if hasattr(app, "SetTestRunRunning"):
            app.SetTestRunRunning(False)

        EndBusyCursorIfRequired()

        logger.debug("")

    def VerifyDatafiles(self, folderModel):
        if folderModel not in self.verifyDatafileRunnable:
            self.verifyDatafileRunnable[folderModel] = []
        for dfi in range(0, folderModel.numFiles):
            if self.IsShuttingDown():
                return
            self.verifyDatafileRunnable[folderModel]\
                .append(VerifyDatafileRunnable(self, self.foldersModel,
                                               folderModel, dfi,
                                               self.settingsModel,
                                               self.testRun))
            if wx.PyApp.IsMainLoopRunning():
                self.verificationsQueue\
                    .put(self.verifyDatafileRunnable[folderModel][dfi])
            else:
                self.verifyDatafileRunnable[folderModel][dfi].Run()

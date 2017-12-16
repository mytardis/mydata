"""
The main controller class for managing datafile verifications
and uploads from each of the folders in the Folders view.
"""
import os
import sys
import time
import threading
# For Python3, this will change to "from queue import Queue":
from Queue import Queue
import traceback
import datetime

import requests
from requests.exceptions import HTTPError

import wx
import wx.lib.newevent
import wx.dataview

import mydata.views.messages
from ..dataviewmodels.dataview import DATAVIEW_MODELS
from ..events import MYDATA_EVENTS
from ..events import PostEvent
from ..events.stop import CheckIfShouldAbort
from ..events import MYDATA_THREADS
from ..settings import SETTINGS
from ..models.experiment import ExperimentModel
from ..models.dataset import DatasetModel
from ..logs import logger
from ..logs.testrun import LogTestRunSummary
from ..utils import EndBusyCursorIfRequired
from ..utils import SafeStr
from ..utils.exceptions import StorageBoxAttributeNotFound
from ..utils.openssh import CleanUpScpAndSshProcesses
from ..threads.flags import FLAGS
from ..threads.locks import LOCKS
from .uploads import UploadMethod
from .uploads import UploadDatafileRunnable
from .verifications import VerifyDatafileRunnable

if sys.platform.startswith("linux"):
    from ..linuxsubprocesses import StartErrandBoy


class FoldersController(object):
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-statements
    """
    The main controller class for managing datafile verifications
    and uploads from each of the folders in the Folders view.
    """
    def __init__(self, parent):
        self.parent = parent

        self.shuttingDown = threading.Event()
        self._canceled = threading.Event()
        self._failed = threading.Event()
        self._started = threading.Event()
        self._completed = threading.Event()

        self.finishedCountingVerifications = dict()
        self.finishedScanningForDatasetFolders = threading.Event()
        self.verificationsQueue = None
        self.uploadsQueue = None
        self.numVerificationsToBePerformed = 0
        self.uploadsAcknowledged = 0
        self.uploadMethod = UploadMethod.HTTP_POST

        # These will get overwritten in InitForUploads, but we need
        # to initialize them here, so that ShutDownUploadThreads()
        # can be called.
        self.numVerificationWorkerThreads = 0
        self.verificationWorkerThreads = []
        self.numUploadWorkerThreads = 0
        self.uploadWorkerThreads = []

        self.countCompletedTimer = None

    @property
    def started(self):
        """
        Return thread-safe flag indicated whether uploads have started
        """
        return self._started.isSet()

    @started.setter
    def started(self, started):
        """
        Set thread-safe flag indicated whether uploads have started
        """
        if started:
            self._started.set()
        else:
            self._started.clear()

    @property
    def canceled(self):
        """
        Return thread-safe flag indicated whether uploads have been canceled

        When FoldersController's ShutDownUploadThreads finishes running, it
        will restore FLAGS.shouldAbort to its default value of False, but
        foldersController.canceled will remain set to True if the last session
        was canceled.  foldersController.canceled will be reset in
        FoldersController's InitializeStatusFlags method the next time we run
        the scans and uploads.
        """
        return self._canceled.isSet()

    @canceled.setter
    def canceled(self, canceled):
        """
        Set thread-safe flag indicated whether uploads have been canceled
        """
        if canceled:
            self._canceled.set()
        else:
            self._canceled.clear()

    @property
    def failed(self):
        """
        Return thread-safe flag indicated whether uploads have failed
        """
        return self._failed.isSet()

    @failed.setter
    def failed(self, failed):
        """
        Set thread-safe flag indicated whether uploads have failed
        """
        if failed:
            self._failed.set()
        else:
            self._failed.clear()

    @property
    def completed(self):
        """
        Return thread-safe flag indicated whether uploads have completed
        """
        return self._completed.isSet()

    @completed.setter
    def completed(self, completed):
        """
        Set thread-safe flag indicated whether uploads have completed
        """
        if completed:
            self._completed.set()
        else:
            self._completed.clear()

    def IsShuttingDown(self):
        """
        Return True if folder scans and uploads are shutting down
        """
        return self.shuttingDown.isSet()

    def SetShuttingDown(self, shuttingDown=True):
        """
        Set to True if folder scans and uploads are shutting down
        """
        if shuttingDown:
            self.shuttingDown.set()
        else:
            self.shuttingDown.clear()

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

        if FLAGS.testRunRunning:
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

        bytesUploadedPreviously = \
            getattr(event, "bytesUploadedPreviously", None)
        verificationModel = getattr(event, "verificationModel", None)
        uploadDatafileRunnable = UploadDatafileRunnable(
            folderModel, dfi, existingUnverifiedDatafile,
            verificationModel, bytesUploadedPreviously)
        if wx.PyApp.IsMainLoopRunning():
            self.uploadsQueue.put(uploadDatafileRunnable)
        else:
            uploadDatafileRunnable.Run()
        self.CountCompletedUploadsAndVerifications(event=None)

    def InitForUploads(self):
        """
        Initialize folders controller in preparation for uploads
        """
        # pylint: disable=too-many-branches
        self.InitializeStatusFlags()
        mydata.views.messages.LAST_ERROR_MESSAGE = None
        mydata.views.messages.LAST_CONFIRMATION_QUESTION = None
        DATAVIEW_MODELS['folders'].ResetCounts()
        DATAVIEW_MODELS['verifications'].DeleteAllRows()
        DATAVIEW_MODELS['uploads'].DeleteAllRows()
        DATAVIEW_MODELS['uploads'].SetStartTime(datetime.datetime.now())
        self.verificationsQueue = Queue()
        self.numVerificationWorkerThreads = \
            SETTINGS.miscellaneous.maxVerificationThreads
        self.verificationWorkerThreads = []
        self.finishedScanningForDatasetFolders = threading.Event()
        self.numVerificationsToBePerformed = 0
        self.uploadsAcknowledged = 0
        self.finishedCountingVerifications = dict()
        SETTINGS.InitializeVerifiedDatafilesCache()

        if wx.PyApp.IsMainLoopRunning():
            for i in range(self.numVerificationWorkerThreads):
                thread = threading.Thread(
                    name="VerificationWorkerThread-%d" % (i + 1),
                    target=self.VerificationWorker)
                self.verificationWorkerThreads.append(thread)
                thread.start()
        self.uploadsQueue = Queue()
        self.numUploadWorkerThreads = SETTINGS.advanced.maxUploadThreads
        self.uploadMethod = UploadMethod.HTTP_POST

        if sys.platform.startswith("linux"):
            StartErrandBoy()

        self.InitializeTimers()

        try:
            SETTINGS.uploaderModel.RequestStagingAccess()
            uploadToStagingRequest = \
                SETTINGS.uploaderModel.uploadToStagingRequest
        except Exception as err:
            # MyData app could be missing from MyTardis server.
            logger.error(traceback.format_exc())
            PostEvent(
                MYDATA_EVENTS.ShowMessageDialogEvent(
                    title="MyData",
                    message=str(err),
                    icon=wx.ICON_ERROR))
            return
        message = None
        if uploadToStagingRequest is None:
            message = "Couldn't determine whether uploads to " \
                      "staging have been approved.  " \
                      "Falling back to HTTP POST."
        elif uploadToStagingRequest.approved:
            location = "UNKNOWN"
            try:
                location = uploadToStagingRequest.location
                _ = uploadToStagingRequest.scpHostname
                _ = uploadToStagingRequest.scpUsername
                logger.info("Uploads to staging have been approved.")
                self.uploadMethod = UploadMethod.VIA_STAGING
            except StorageBoxAttributeNotFound as err:
                message = SafeStr(err)

                def StopUploadsAsFailed(showError=False):
                    """
                    Shutdown uploads with the reason: failed.
                    """
                    logger.error(message)
                    self.failed = True
                    FLAGS.shouldAbort = True
                    PostEvent(MYDATA_EVENTS.ShutdownUploadsEvent(failed=True))
                    if showError:
                        PostEvent(
                            MYDATA_EVENTS.ShowMessageDialogEvent(
                                title="MyData", message=message,
                                icon=wx.ICON_ERROR))

                if "scp_" in err.key:
                    logger.warning(message)
                    question = (
                        "The %s storage box attribute is missing from "
                        "the assigned storage box.\n\n"
                        "Do you want MyData to attempt to access the storage "
                        "box location (%s) locally (e.g. via a mounted file "
                        "share)?" % (err.key, location))
                    logger.info(question)

                    def OnYes():
                        """
                        User clicked Yes
                        """
                        self.uploadMethod = UploadMethod.LOCAL_COPY

                    if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ:
                        with LOCKS.displayModalDialog:
                            PostEvent(
                                MYDATA_EVENTS.ShowConfirmationDialogEvent(
                                    title="MyData", question=question,
                                    onYes=OnYes, onNo=StopUploadsAsFailed))
                            # Wait for confirmation dialog to appear:
                            while not FLAGS.showingConfirmationDialog:
                                time.sleep(0.1)
                            # Wait for confirmation dialog to close:
                            while FLAGS.showingConfirmationDialog:
                                time.sleep(0.1)
                    else:
                        StopUploadsAsFailed(showError=True)
                        return
                else:
                    StopUploadsAsFailed(showError=True)
                    return
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
            logger.warning(message)
            PostEvent(
                MYDATA_EVENTS.ShowMessageDialogEvent(
                    title="MyData",
                    message=message,
                    icon=wx.ICON_WARNING))
            self.uploadMethod = UploadMethod.HTTP_POST
        if self.uploadMethod == UploadMethod.HTTP_POST and \
                self.numUploadWorkerThreads > 1:
            logger.warning(
                "Using HTTP POST, so setting "
                "numUploadWorkerThreads to 1, "
                "because urllib2 is not thread-safe.")
            self.numUploadWorkerThreads = 1

        self.uploadWorkerThreads = []
        if wx.PyApp.IsMainLoopRunning():
            for i in range(self.numUploadWorkerThreads):
                thread = threading.Thread(
                    name="UploadWorkerThread-%d" % (i + 1),
                    target=self.UploadWorker, args=())
                self.uploadWorkerThreads.append(thread)
                thread.start()

    def InitializeTimers(self):
        """
        These timers control how often components of the GUI are updated
        which can't be updated every time the underlying data changes,
        because it changes too quickly.

        Timers do not run in unit tests.

        This method is usually run from a worker thread, hence the use of
        wx.CallAfter
        """
        self.countCompletedTimer = wx.Timer(self.parent)
        self.parent.Bind(wx.EVT_TIMER, self.CountCompletedUploadsAndVerifications,
                         self.countCompletedTimer)
        if 'MYDATA_TESTING' not in os.environ:
            wx.CallAfter(self.countCompletedTimer.Start, 500)
            wx.CallAfter(self.parent.dataViews['verifications'] \
                    .updateCacheHitSummaryTimer.Start, 500)

    def StopTimers(self):
        """
        These timers control how often components of the GUI are updated
        which can't be updated every time the underlying data changes,
        because it changes too quickly.

        Timers do not run in unit tests.

        This method is currently run from the main thread, hence the lack of
        wx.CallAfter when stopping the timers.
        """
        assert threading.current_thread().name == "MainThread"
        if 'MYDATA_TESTING' not in os.environ:
            self.parent.dataViews['verifications'] \
                .updateCacheHitSummaryTimer.Stop()
            self.parent.dataViews['verifications'].UpdateCacheHitSummary(None)
            self.countCompletedTimer.Stop()

    def ClearStatusFlags(self):
        """
        Clear flags which indicate the status of the scans and uploads
        (started, canceled, completed etc.)  These assignments use the
        FoldersController class's property setter methods to update the
        status of threading.Event() objects.

        This method is called by the MyData app class's
        ResetShouldAbortStatus method.
        """
        self.started = False
        self.canceled = False
        self.failed = False
        self.completed = False

    def InitializeStatusFlags(self):
        """
        Initialize flags which indicate the status of the scans and uploads
        (started, canceled, completed etc.)  These assignments use the
        FoldersController class's property setter methods to update the
        status of threading.Event() objects.

        This method is called by InitForUploads, but it may also be called
        earlier in tests where we want to ensure that the status flags are
        set (or reset) before we test canceling the scans and uploads.
        """
        FLAGS.shouldAbort = False
        self.started = True
        self.canceled = False
        self.failed = False
        self.completed = False

    def FinishedScanningForDatasetFolders(self):
        """
        At this point, we know that FoldersModel's
        ScanFolders method has finished populating
        DATAVIEW_MODELS['folders'] with dataset folders.
        """
        while len(self.finishedCountingVerifications.keys()) < \
                DATAVIEW_MODELS['folders'].GetCount():
            if self.IsShuttingDown() or CheckIfShouldAbort():
                break
            time.sleep(0.01)
        logger.debug("Finished scanning for dataset folders.")
        self.finishedScanningForDatasetFolders.set()
        if wx.PyApp.IsMainLoopRunning():
            wx.CallAfter(self.CountCompletedUploadsAndVerifications, event=None)
        else:
            self.CountCompletedUploadsAndVerifications(event=None)

    def StartUploadsForFolder(self, folderModel):
        """
        Start uploads for the specified folder
        """
        # pylint: disable=too-many-branches
        if CheckIfShouldAbort():
            return
        try:
            with LOCKS.finishedCounting:
                self.finishedCountingVerifications[folderModel] = \
                    threading.Event()
            if self.IsShuttingDown() or CheckIfShouldAbort():
                return
            with LOCKS.numVerificationsToBePerformed:
                self.numVerificationsToBePerformed += folderModel.GetNumFiles()
            logger.debug(
                "StartUploadsForFolder: Starting verifications "
                "and uploads for folder: " + folderModel.folderName)
            if self.IsShuttingDown() or CheckIfShouldAbort():
                return
            try:
                try:
                    with LOCKS.getOrCreateExp:
                        experimentModel = ExperimentModel\
                            .GetOrCreateExperimentForFolder(folderModel)
                except Exception as err:
                    if self.failed:
                        return
                    message = str(err)
                    if isinstance(err, HTTPError) and \
                            err.response.status_code == 500:
                        logger.error(err.response.request.url)
                        try:
                            error = ("Internal Server Error: %s"
                                     % err.response.json()['error_message'])
                            logger.error(error)
                            info = "See the Log for more information."
                            logger.error(err.response.json()['traceback'])
                        except:
                            error = "An Internal Server Error occurred."
                            info = (
                                "For more information, set DEBUG to True in "
                                "MyTardis's settings.")
                            logger.error(info)
                        message = ("%s\n\n%s\n\n%s"
                                   % (error, err.response.request.url, info))
                        PostEvent(
                            MYDATA_EVENTS.ShowMessageDialogEvent(
                                title="MyData", message=message,
                                icon=wx.ICON_ERROR))
                    elif isinstance(err, HTTPError) and not message:
                        message = ("Received %s (%s) response from server."
                                   % (type(err).__name__,
                                      err.response.status_code))
                        message = ("%s\n\n%s"
                                   % (message, err.response.request.url))
                        logger.error(message)
                    else:
                        logger.error(traceback.format_exc())
                    if not self.failed:
                        self.failed = True
                        FLAGS.shouldAbort = True
                        PostEvent(
                            MYDATA_EVENTS.ShowMessageDialogEvent(
                                title="MyData", message=message,
                                icon=wx.ICON_ERROR))
                        PostEvent(MYDATA_EVENTS.ShutdownUploadsEvent(failed=True))
                    return
                folderModel.experimentModel = experimentModel
                try:
                    folderModel.datasetModel = DatasetModel\
                        .CreateDatasetIfNecessary(folderModel)
                except Exception as err:
                    logger.error(traceback.format_exc())
                    PostEvent(
                        MYDATA_EVENTS.ShowMessageDialogEvent(
                            title="MyData",
                            message=str(err),
                            icon=wx.ICON_ERROR))
                    return
                self.VerifyDatafiles(folderModel)
            except requests.exceptions.ConnectionError as err:
                logger.error(str(err))
                return
            except ValueError:
                logger.error("Failed to retrieve experiment "
                             "for folder " + folderModel.folderName)
                logger.error(traceback.format_exc())
                return
            if experimentModel is None and not FLAGS.testRunRunning:
                logger.error("Failed to acquire a MyTardis "
                             "experiment to store data in for "
                             "folder " + folderModel.folderName)
                return
            if self.IsShuttingDown() or CheckIfShouldAbort():
                return
            with LOCKS.finishedCounting:
                self.finishedCountingVerifications[folderModel].set()
            if DATAVIEW_MODELS['folders'].GetRowCount() == 0 or \
                    self.numVerificationsToBePerformed == 0:
                # For the case of zero folders or zero files, we
                # can't use the usual triggers (e.g. datafile
                # upload complete) to determine when to check if
                # we have finished:
                self.CountCompletedUploadsAndVerifications(event=None)
        except:
            logger.error(traceback.format_exc())

    def UploadWorker(self):
        # Could be moved to uploads controller
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
                else:
                    logger.error(traceback.format_exc())
                    self.uploadsQueue.task_done()
                return
            except:
                logger.error(traceback.format_exc())
                self.uploadsQueue.task_done()
                return

    def VerificationWorker(self):
        # Could be moved to verifications controller
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
        if self.completed or self.canceled:
            return

        assert threading.current_thread().name == "MainThread"

        # Tell the folders view to refresh its data.  (It was previously
        # updated only when a changed was made to the underlying data, but
        # because changes coming from the cache are two quick, we can't use
        # these changes as the trigger to update the view any longer:
        # The lock prevents RuntimeError: deque mutated during iteration
        with LOCKS.foldersToUpdate:
            for folder in DATAVIEW_MODELS['folders'].foldersToUpdate:
                DATAVIEW_MODELS['folders'].FolderStatusUpdated(folder)
            DATAVIEW_MODELS['folders'].foldersToUpdate.clear()

        numVerificationsCompleted = \
            DATAVIEW_MODELS['verifications'].GetCompletedCount()

        uploadsToBePerformed = DATAVIEW_MODELS['uploads'].GetRowCount() + \
            self.uploadsQueue.qsize()

        uploadsCompleted = DATAVIEW_MODELS['uploads'].GetCompletedCount()
        uploadsFailed = DATAVIEW_MODELS['uploads'].GetFailedCount()
        uploadsProcessed = uploadsCompleted + uploadsFailed

        if hasattr(wx.GetApp(), "frame") and numVerificationsCompleted > 0:
            if numVerificationsCompleted == \
                    self.numVerificationsToBePerformed \
                    and uploadsToBePerformed > 0:
                message = "Uploaded %d of %d files." % \
                    (uploadsCompleted, uploadsToBePerformed)
            else:
                message = "Looked up %d of %d files." % \
                    (numVerificationsCompleted,
                     self.numVerificationsToBePerformed)
            wx.CallAfter(wx.GetApp().frame.SetStatusMessage, message)

        finishedVerificationCounting = \
            self.finishedScanningForDatasetFolders.isSet()
        # Use lock to avoid "dictionary changed size during iteration" error:
        with LOCKS.finishedCounting:
            for folder in self.finishedCountingVerifications:
                if not self.finishedCountingVerifications[folder]:
                    finishedVerificationCounting = False
                    break

        if numVerificationsCompleted == self.numVerificationsToBePerformed \
                and finishedVerificationCounting \
                and (uploadsProcessed == uploadsToBePerformed or
                     FLAGS.testRunRunning and
                     self.uploadsAcknowledged == uploadsToBePerformed):
            logger.debug("All datafile verifications and uploads "
                         "have completed.")
            logger.debug("Shutting down upload and verification threads.")
            PostEvent(MYDATA_EVENTS.ShutdownUploadsEvent(completed=True))
        elif not wx.PyApp.IsMainLoopRunning() and FLAGS.testRunRunning and \
                finishedVerificationCounting:
            PostEvent(MYDATA_EVENTS.ShutdownUploadsEvent(completed=True))

    def ShutDownUploadThreads(self, event=None):
        """
        Shut down upload threads
        """
        # pylint: disable=too-many-branches
        if self.IsShuttingDown() or self.completed or self.canceled:
            return

        assert threading.current_thread().name == "MainThread"

        self.SetShuttingDown(True)
        app = wx.GetApp()
        if SETTINGS.miscellaneous.cacheDataFileLookups:
            threading.Thread(
                target=SETTINGS.SaveVerifiedDatafilesCache).start()
        # Reset self.started so that scheduled tasks know that's OK to start
        # new scan-and-upload tasks:
        self.started = False
        if not FLAGS.performingLookupsAndUploads:
            # This means StartUploadsForFolder was never called
            EndBusyCursorIfRequired()
            if CheckIfShouldAbort():
                message = "Data scans and uploads were canceled."
                self.canceled = True
            else:
                message = "No folders were found to upload from."
                self.completed = True
            if hasattr(app, "frame"):
                app.frame.toolbar.EnableTestAndUploadToolbarButtons()
                FLAGS.shouldAbort = False
                if FLAGS.testRunRunning:
                    app.testRunFrame.saveButton.Enable()
            logger.info(message)
            if hasattr(app, "frame"):
                app.frame.SetStatusMessage(message, force=True)
            self.SetShuttingDown(False)
            return
        message = "Shutting down upload threads..."
        logger.info(message)
        self.StopTimers()
        if hasattr(app, "frame"):
            app.frame.SetStatusMessage(message, force=True)
        if hasattr(event, "failed") and event.failed:
            self.failed = True
            DATAVIEW_MODELS['uploads'].CancelRemaining()
        elif hasattr(event, "completed") and event.completed:
            self.completed = True
        else:
            self.canceled = True
            DATAVIEW_MODELS['uploads'].CancelRemaining()
        logger.debug("Shutting down FoldersController upload worker threads.")
        for _ in range(self.numUploadWorkerThreads):
            self.uploadsQueue.put(None)
        if self.uploadMethod == UploadMethod.VIA_STAGING:
            # SCP can leave orphaned SSH processes which need to be
            # cleaned up.
            # Give each UploadModel instance's Cancel() method a chance to
            # terminate its SCP process first:
            time.sleep(0.1)
            CleanUpScpAndSshProcesses()
        for thread in self.uploadWorkerThreads:
            thread.join()
        logger.debug("Shutting down FoldersController verification "
                     "worker threads.")
        for _ in range(self.numVerificationWorkerThreads):
            self.verificationsQueue.put(None)
        for thread in self.verificationWorkerThreads:
            thread.join()

        logger.debug("Joining remaining threads...")
        MYDATA_THREADS.Join()
        logger.debug("Joined remaining threads.")

        if FLAGS.testRunRunning:
            LogTestRunSummary()

        if self.failed:
            message = "Data scans and uploads failed."
        elif self.canceled:
            message = "Data scans and uploads were canceled."
        elif DATAVIEW_MODELS['uploads'].GetFailedCount() > 0:
            message = \
                "Data scans and uploads completed with " \
                "%d failed upload(s)." % DATAVIEW_MODELS['uploads'].GetFailedCount()
        elif self.completed:
            if DATAVIEW_MODELS['uploads'].GetCompletedCount() > 0:
                message = "Data scans and uploads completed successfully."
                elapsedTime = DATAVIEW_MODELS['uploads'].GetElapsedTime()
                if elapsedTime and not FLAGS.testRunRunning:
                    averageSpeedMBs = \
                        (float(DATAVIEW_MODELS['uploads'].GetCompletedSize()) /
                         1000000.0 / elapsedTime.total_seconds())
                    if averageSpeedMBs >= 1.0:
                        averageSpeed = "%3.1f MB/s" % averageSpeedMBs
                    else:
                        averageSpeed = \
                            "%3.1f KB/s" % (averageSpeedMBs * 1000.0)
                    message += "  Average speed: %s" % averageSpeed
            else:
                if FLAGS.testRunRunning:
                    if self.uploadsAcknowledged > 0:
                        message = \
                            "Finished scanning with %s files requiring upload." \
                            % self.uploadsAcknowledged
                    else:
                        message = "No new files were found to upload."
                else:
                    message = "No new files were found to upload."
        else:
            message = "Data scans and uploads appear to have " \
                "completed successfully."
        logger.info(message)
        if hasattr(app, "frame"):
            app.frame.SetStatusMessage(message, force=True)
        if FLAGS.testRunRunning:
            logger.testrun(message)

        if hasattr(app, "frame"):
            app.frame.toolbar.EnableTestAndUploadToolbarButtons()
            FLAGS.shouldAbort = False
            if FLAGS.testRunRunning:
                app.testRunFrame.saveButton.Enable()
        FLAGS.performingLookupsAndUploads = False
        FLAGS.scanningFolders = False
        self.SetShuttingDown(False)
        FLAGS.testRunRunning = False

        EndBusyCursorIfRequired()

        logger.debug("")

    def VerifyDatafiles(self, folderModel):
        """
        Verify datafiles in the specified folder
        """
        for dfi in range(0, folderModel.numFiles):
            if self.IsShuttingDown():
                return
            verifyDatafileRunnable = VerifyDatafileRunnable(folderModel, dfi)
            if wx.PyApp.IsMainLoopRunning():
                self.verificationsQueue.put(verifyDatafileRunnable)
            else:
                verifyDatafileRunnable.Run()

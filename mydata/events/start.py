"""
mydata/events/start.py

This module contains methods relating to starting MyData's scan-and-upload
processes.

The main method this module provides is "StartScansAndUploads", which is
called by the ScheduleController's ApplySchedule method, which is called
when the user clicks MyData's "Upload" toolbar button, and in response
to various other events.
"""
import traceback
import threading

import wx

from ..settings import SETTINGS
from ..dataviewmodels.users import UsersModel
from ..dataviewmodels.dataview import DATAVIEW_MODELS
from ..models.settings import LastSettingsUpdateTrigger
from ..models.settings.validation import ValidateSettings
from ..utils.exceptions import InvalidFolderStructure
from ..utils.exceptions import InvalidSettings
from ..utils.exceptions import UserAbortedSettingsValidation
from ..logs import logger
from ..events import MYDATA_EVENTS
from ..events import PostEvent
from ..utils import BeginBusyCursorIfRequired
from ..utils import EndBusyCursorIfRequired
from ..utils import HandleGenericErrorWithDialog
from ..utils.connectivity import CONNECTIVITY
from ..utils.connectivity import GetActiveNetworkInterfaces
from ..threads.flags import FLAGS
from ..threads.locks import LOCKS
from ..views.connectivity import ReportNoActiveInterfaces


def OnScanAndUploadFromToolbar(event):
    """
    The user pressed the Upload icon on the main window's toolbar.
    """
    logger.debug("OnScanAndUploadFromToolbar")
    ManuallyTriggerScanFoldersAndUpload(event)


def ManuallyTriggerScanFoldersAndUpload(event):
    """
    Scan folders and upload datafiles if necessary.
    """
    from .stop import ResetShouldAbortStatus
    app = wx.GetApp()
    SETTINGS.schedule.scheduleType = "Manually"
    SETTINGS.lastSettingsUpdateTrigger = LastSettingsUpdateTrigger.UI_RESPONSE
    ResetShouldAbortStatus()
    app.scheduleController.ApplySchedule(event, runManually=True)


def StartScansAndUploads(
        event, needToValidateSettings=True, jobId=None, testRun=False):
    """
    Shut down any existing data folder scan and upload threads,
    validate settings, and begin scanning data folders, checking
    for existing datafiles on MyTardis and uploading any datafiles
    not yet available on MyTardis.
    """
    from .stop import CheckIfShouldAbort
    from .stop import RestoreUserInterfaceForAbort
    app = wx.GetApp()
    LogStartScansAndUploadsCaller(event, jobId)
    if CheckIfShouldAbort():
        return
    shutdownForRefreshComplete = event and \
        event.GetEventType() in (
            MYDATA_EVENTS.EVT_SHUTDOWN_FOR_REFRESH_COMPLETE,
            MYDATA_EVENTS.EVT_SETTINGS_VALIDATION_COMPLETE)
    if hasattr(event, "needToValidateSettings") and \
            not event.needToValidateSettings:
        needToValidateSettings = False
    if hasattr(event, "shutdownSuccessful") and event.shutdownSuccessful:
        shutdownForRefreshComplete = True
    if hasattr(event, "testRun") and event.testRun:
        testRun = True

    if (FLAGS.scanningFolders or FLAGS.performingLookupsAndUploads) \
            and not shutdownForRefreshComplete:
        # Shuts down upload threads before restarting them when
        # a scan and upload task is due to start while another
        # scan and upload task is already running:
        message = \
            "Shutting down existing data scan and upload processes..."
        logger.debug(message)
        app.frame.SetStatusMessage(message)

        shutdownForRefreshEvent = \
            MYDATA_EVENTS.ShutdownForRefreshEvent(testRun=testRun)
        logger.debug("Posting shutdownForRefreshEvent")
        PostEvent(shutdownForRefreshEvent)
        return

    app.foldersController.SetShuttingDown(False)

    app.frame.toolbar.searchCtrl.SetValue("")

    # Settings validation:

    if needToValidateSettings:
        validateSettingsForRefreshEvent = \
            MYDATA_EVENTS.ValidateSettingsForRefreshEvent(
                needToValidateSettings=needToValidateSettings,
                testRun=testRun)
        if CONNECTIVITY.CheckForRefresh(
                nextEvent=validateSettingsForRefreshEvent):
            # Wait for the event to be handled, which will result
            # in StartScansAndUploads being called again.
            return

        logger.debug("StartScansAndUploads: needToValidateSettings is True.")
        message = "Validating settings..."
        app.frame.SetStatusMessage(message)
        logger.info(message)
        if testRun:
            logger.testrun(message)

        def ValidateSettingsWorker():
            """
            Validate settings.
            """
            from .settings import OnSettings
            logger.debug("Starting run() method for thread %s"
                         % threading.current_thread().name)
            activeNetworkInterfaces = []
            try:
                wx.CallAfter(BeginBusyCursorIfRequired)
                try:
                    activeNetworkInterfaces = GetActiveNetworkInterfaces()
                except Exception as err:
                    HandleGenericErrorWithDialog(err)
                if not activeNetworkInterfaces:
                    ReportNoActiveInterfaces()
                    return

                try:
                    ValidateSettings(testRun=testRun)
                    event = MYDATA_EVENTS.SettingsValidationCompleteEvent(
                        testRun=testRun)
                    PostEvent(event)
                    wx.CallAfter(EndBusyCursorIfRequired)
                except UserAbortedSettingsValidation:
                    RestoreUserInterfaceForAbort()
                    return
                except InvalidSettings as invalidSettings:
                    # If settings validation is run automatically shortly
                    # after a scheduled task begins, ignore complaints from
                    # settings validation about the "scheduled_time" being
                    # in the past.  Any other settings validation failure
                    # will be reported.
                    field = invalidSettings.field
                    if field != "scheduled_time":
                        logger.debug(
                            "Displaying result from settings validation.")
                        message = invalidSettings.message
                        logger.error(message)
                        RestoreUserInterfaceForAbort()
                        wx.CallAfter(app.frame.SetStatusMessage,
                            "Settings validation failed.")
                        if testRun:
                            wx.CallAfter(app.testRunFrame.Hide)
                        wx.CallAfter(OnSettings, None,
                                     validationMessage=message)
                        return
            except:
                logger.error(traceback.format_exc())
                return
            logger.debug("Finishing run() method for thread %s"
                         % threading.current_thread().name)

        if wx.PyApp.IsMainLoopRunning():
            thread = threading.Thread(
                target=ValidateSettingsWorker,
                name="StartScansAndUploadsValidateSettingsThread")
            logger.debug("Starting thread %s" % thread.name)
            thread.start()
            logger.debug("Started thread %s" % thread.name)
        else:
            ValidateSettingsWorker()
        return

    def WriteProgressUpdateToStatusBar(numUserOrGroupFoldersScanned):
        """
        Write progress update to status bar.
        """
        message = "Scanned %d of %d %s folders" % (
            numUserOrGroupFoldersScanned,
            UsersModel.GetNumUserOrGroupFolders(),
            SETTINGS.advanced.userOrGroupString)
        if FLAGS.shouldAbort or not FLAGS.scanningFolders:
            return
        app.frame.SetStatusMessage(message)
        if numUserOrGroupFoldersScanned == \
                UsersModel.GetNumUserOrGroupFolders():
            logger.info(message)
            if testRun:
                logger.testrun(message)

    # Start FoldersModel.ScanFolders()

    def ScanDataDirs():
        """
        Scan data folders, looking for datafiles to look up on MyTardis
        and upload if necessary.
        """
        from .stop import CheckIfShouldAbort
        if CheckIfShouldAbort():
            return
        app.foldersController.InitForUploads()
        if CheckIfShouldAbort():
            return
        message = "Scanning data folders..."
        wx.CallAfter(app.frame.SetStatusMessage, message)
        message = "Scanning data folders in %s..." \
            % SETTINGS.general.dataDirectory
        logger.info(message)
        if testRun:
            logger.testrun(message)
        try:
            LOCKS.scanningFolders.acquire()
            FLAGS.scanningFolders = True
            logger.debug("Just set scanningFolders to True")
            wx.CallAfter(
                app.frame.toolbar.DisableTestAndUploadToolbarButtons)
            DATAVIEW_MODELS['folders'].ScanFolders(
                WriteProgressUpdateToStatusBar)
            app.foldersController.FinishedScanningForDatasetFolders()
            FLAGS.scanningFolders = False
            LOCKS.scanningFolders.release()
            logger.debug("Just set scanningFolders to False")
        except InvalidFolderStructure as ifs:
            def ShowMessageDialog():
                """
                Needs to run in the main thread.
                """
                dlg = wx.MessageDialog(None, str(ifs), "MyData",
                                       wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
            wx.CallAfter(ShowMessageDialog)
            wx.CallAfter(app.frame.SetStatusMessage, str(ifs))
            return

        if CheckIfShouldAbort():
            RestoreUserInterfaceForAbort()
            if testRun:
                logger.testrun("Data scans and uploads were canceled.")
                FLAGS.testRunRunning = False
            return

        folderStructure = SETTINGS.advanced.folderStructure
        usersModel = DATAVIEW_MODELS['users']
        groupsModel = DATAVIEW_MODELS['groups']
        if any([
                UsersModel.GetNumUserOrGroupFolders() == 0,
                folderStructure.startswith("Username") and
                usersModel.GetCount() == 0,
                folderStructure.startswith("Email") and
                usersModel.GetCount() == 0,
                folderStructure.startswith("User Group") and
                groupsModel.GetCount() == 0]):
            if UsersModel.GetNumUserOrGroupFolders() == 0:
                message = "No folders were found to upload from."
            else:
                message = "No valid folders were found to upload from."
            logger.warning(message)
            if testRun:
                logger.testrun(message)
            wx.CallAfter(app.frame.SetStatusMessage, message)
            RestoreUserInterfaceForAbort()
        wx.CallAfter(EndBusyCursorIfRequired)

    if wx.PyApp.IsMainLoopRunning():
        thread = threading.Thread(target=ScanDataDirs,
                                  name="ScanDataDirectoriesThread")
        thread.start()
    else:
        ScanDataDirs()


def LogStartScansAndUploadsCaller(event, jobId):
    """
    Called by StartScansAndUploads (the main method for starting the
    data folder scans and uploads) to log what triggered the
    call to StartScansAndUploads (e.g. the toolbar button, the task bar
    icon menu item, or a scheduled task).
    """
    app = wx.GetApp()
    try:
        syncNowMenuItemId = \
            app.frame.taskBarIcon.GetSyncNowMenuItem().GetId()
    except (AttributeError, RuntimeError):
        syncNowMenuItemId = None
    if jobId:
        logger.debug("StartScansAndUploads called from job ID %d" % jobId)
    elif event is None:
        logger.debug("StartScansAndUploads called automatically "
                     "from MyData's OnInit().")
    elif event.GetId() == app.frame.toolbar.settingsTool.GetId():
        logger.debug("StartScansAndUploads called automatically from "
                     "OnSettings(), after displaying SettingsDialog, "
                     "which was launched from MyData's toolbar.")
    elif event.GetId() == app.frame.toolbar.uploadTool.GetId():
        logger.debug("StartScansAndUploads triggered by Upload toolbar icon.")
    elif syncNowMenuItemId and event.GetId() == syncNowMenuItemId:
        logger.debug("StartScansAndUploads triggered by 'Sync Now' "
                     "task bar menu item.")
    elif event.GetEventType() == \
            MYDATA_EVENTS.EVT_VALIDATE_SETTINGS_FOR_REFRESH:
        logger.debug("StartScansAndUploads called from "
                     "EVT_VALIDATE_SETTINGS_FOR_REFRESH event.")
    elif event.GetEventType() == \
            MYDATA_EVENTS.EVT_SETTINGS_VALIDATION_COMPLETE:
        logger.debug("StartScansAndUploads called from "
                     "EVT_SETTINGS_VALIDATION_COMPLETE event.")
    elif event.GetEventType() == \
            MYDATA_EVENTS.EVT_SHUTDOWN_FOR_REFRESH_COMPLETE:
        logger.debug("StartScansAndUploads called from "
                     "EVT_SHUTDOWN_FOR_REFRESH_COMPLETE event.")
    elif event.GetEventType() == \
            MYDATA_EVENTS.EVT_SETTINGS_VALIDATION_COMPLETE:
        logger.debug("StartScansAndUploads called from "
                     "EVT_SETTINGS_VALIDATION_COMPLETE event.")
    else:
        logger.debug("StartScansAndUploads: event.GetEventType() = %s"
                     % event.GetEventType())


def OnTestRunFromToolbar(event):
    """
    The user pressed the Test Run icon on the main window's toolbar.
    """
    from .stop import ResetShouldAbortStatus
    app = wx.GetApp()
    logger.debug("OnTestRunFromToolbar")
    FLAGS.testRunRunning = True
    SETTINGS.schedule.scheduleType = "Manually"
    SETTINGS.lastSettingsUpdateTrigger = LastSettingsUpdateTrigger.UI_RESPONSE
    app.frame.toolbar.DisableTestAndUploadToolbarButtons()
    app.testRunFrame.saveButton.Disable()
    ResetShouldAbortStatus()
    app.scheduleController.ApplySchedule(event, runManually=True,
                                         needToValidateSettings=True,
                                         testRun=True)
    app.testRunFrame.Show()
    app.testRunFrame.Clear()
    app.testRunFrame.SetTitle("%s - Test Run" % app.frame.GetTitle())
    logger.testrun("Starting Test Run...")

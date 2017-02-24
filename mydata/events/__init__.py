"""
Custom events for MyData.
"""
import threading
from datetime import datetime
import traceback
import sys
import logging
import wx

from ..models.settings.serialize import SaveFieldsFromDialog
from ..models.settings.validation import ValidateSettings
from ..models.uploader import UploaderModel
from ..utils.exceptions import DuplicateKey
from ..utils.exceptions import UserAbortedSettingsValidation
from ..utils.exceptions import InvalidSettings
from ..utils import BeginBusyCursorIfRequired
from ..utils import EndBusyCursorIfRequired
from ..logs import logger
from ..views.connectivity import ReportNoActiveInterfaces


def NewEvent(defaultTarget=None, defaultHandler=None):
    """Generate new (Event, Binder) tuple
        e.g. MooEvent, EVT_MOO = NewEvent()
    """
    eventType = wx.NewEventType()

    class Event(wx.PyEvent):
        """ Custom event class """
        defaultEventTarget = defaultTarget
        defaultEventHandler = defaultHandler

        @staticmethod
        def GetDefaultTarget():
            """ Return default target. """
            return Event.defaultEventTarget

        @staticmethod
        def GetDefaultHandler():
            """ Return default handler. """
            return Event.defaultEventHandler

        def __init__(self, **kw):
            wx.PyEvent.__init__(self)
            self.SetEventType(eventType)
            self.__dict__.update(kw)

    eventBinder = wx.PyEventBinder(eventType)

    if defaultTarget and defaultHandler:
        defaultTarget.Bind(eventBinder, defaultHandler)

    return Event, eventType, eventBinder


def PostEvent(event):
    """
    For now, just call wx.PostEvent, but later this will be able to call the
    event's default handler directly if necessary, eliminating the dependency
    on wxPython's event loop.  This is useful for automated testing.
    """
    # pylint: disable=too-many-branches
    app = wx.GetApp()
    eventTypeId = event.GetEventType()
    eventTypeString = None
    if logger.GetLevel() == logging.DEBUG:
        keys = dir(MYDATA_EVENTS)
        for key in keys:
            if key.startswith("EVT_") and \
                    MYDATA_EVENTS.__dict__[key] == eventTypeId:
                eventTypeString = key
                logger.debug("Posting %s" % eventTypeString)
        if hasattr(app, "foldersController"):
            keys = dir(app.foldersController)
            for key in keys:
                if key.startswith("EVT_") and \
                        app.foldersController.__dict__[key] == eventTypeId:
                    eventTypeString = key
                    logger.debug("Posting %s" % eventTypeString)
    if wx.PyApp.IsMainLoopRunning():
        target = event.GetDefaultTarget()
        if not target:
            target = app.GetMainFrame()
        wx.PostEvent(target, event)
    else:
        if hasattr(event, "GetDefaultHandler"):
            if not eventTypeString:
                eventTypeString = str(eventTypeId)
            logger.debug("Calling default handler for %s" % eventTypeString)
            event.GetDefaultHandler()(event)
            logger.debug("Called default handler for %s" % eventTypeString)
        else:
            logger.debug("Didn't find default handler for %s"
                         % eventTypeString)


class MyDataEvents(object):
    """
    Custom events for MyData.
    """
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=invalid-name
    def __init__(self):
        self.notifyWindow = None
        self.ShutdownForRefreshEvent = None
        self.EVT_SHUTDOWN_FOR_REFRESH = None
        self.ShutdownForRefreshCompleteEvent = None
        self.EVT_SHUTDOWN_FOR_REFRESH_COMPLETE = None
        self.ValidateSettingsForRefreshEvent = None
        self.EVT_VALIDATE_SETTINGS_FOR_REFRESH = None
        self.CheckConnectivityEvent = None
        self.EVT_CHECK_CONNECTIVITY = None
        self.InstrumentNameMismatchEvent = None
        self.EVT_INSTRUMENT_NAME_MISMATCH = None
        self.RenameInstrumentEvent = None
        self.EVT_RENAME_INSTRUMENT = None
        self.SettingsDialogValidationEvent = None
        self.EVT_SETTINGS_DIALOG_VALIDATION = None
        self.ProvideSettingsValidationResultsEvent = None
        self.EVT_PROVIDE_SETTINGS_VALIDATION_RESULTS = None
        self.SettingsValidationCompleteEvent = None
        self.EVT_SETTINGS_VALIDATION_COMPLETE = None
        self.StartUploadsForFolderEvent = None
        self.EVT_START_UPLOADS_FOR_FOLDER = None

    def InitializeWithNotifyWindow(self, notifyWindow):
        """
        Set notify window (main frame), and create event classes using the
        NewEvent function above which automatically binds events to their
        default handler.
        """
        self.notifyWindow = notifyWindow
        self.ShutdownForRefreshEvent, \
            self.EVT_SHUTDOWN_FOR_REFRESH, _ = \
            NewEvent(notifyWindow, ShutdownForRefresh)
        self.ShutdownForRefreshCompleteEvent, \
            self.EVT_SHUTDOWN_FOR_REFRESH_COMPLETE, _ = \
            NewEvent(notifyWindow, ShutdownForRefreshComplete)
        self.ValidateSettingsForRefreshEvent, \
            self.EVT_VALIDATE_SETTINGS_FOR_REFRESH, _ = \
            NewEvent(notifyWindow, ValidateSettingsForRefresh)
        self.CheckConnectivityEvent, \
            self.EVT_CHECK_CONNECTIVITY, _ = \
            NewEvent(notifyWindow, CheckConnectivity)
        self.InstrumentNameMismatchEvent, \
            self.EVT_INSTRUMENT_NAME_MISMATCH, _ = \
            NewEvent(notifyWindow, InstrumentNameMismatch)
        self.RenameInstrumentEvent, \
            self.EVT_RENAME_INSTRUMENT, _ = \
            NewEvent(notifyWindow, RenameInstrument)
        self.SettingsDialogValidationEvent, \
            self.EVT_SETTINGS_DIALOG_VALIDATION, _ = \
            NewEvent(notifyWindow, SettingsDialogValidation)
        self.ProvideSettingsValidationResultsEvent, \
            self.EVT_PROVIDE_SETTINGS_VALIDATION_RESULTS, _ = \
            NewEvent(notifyWindow, ProvideSettingsValidationResults)
        self.SettingsValidationCompleteEvent, \
            self.EVT_SETTINGS_VALIDATION_COMPLETE, _ = \
            NewEvent(notifyWindow, SettingsValidationForRefreshComplete)
        self.StartUploadsForFolderEvent, \
            self.EVT_START_UPLOADS_FOR_FOLDER, _ = \
            NewEvent(notifyWindow, StartDataUploadsForFolder)

    def GetNotifyWindow(self):
        """
        Returns the wx.Frame which propagates events,
        which is MyData's main frame..
        """
        return self.notifyWindow


MYDATA_EVENTS = MyDataEvents()


class MyDataThreads(object):
    """
    Thread pool for MyData.
    """
    def __init__(self):
        self.threads = []

    def __str__(self):
        return str(self.threads)

    def Add(self, thread):
        """
        Register additional thread.
        """
        self.threads.append(thread)

    def Join(self):
        """
        Join threads.
        """
        for thread in self.threads:
            thread.join()
            logger.debug("\tJoined %s" % thread.name)


MYDATA_THREADS = MyDataThreads()


def ShutdownForRefresh(event):
    """
    Shuts down upload threads before restarting them when
    a scan and upload task is due to start while another
    scan and upload task is already running.
    """

    def ShutdownForRefreshWorker():
        """
        Shuts down upload threads (in dedicated worker thread)
        before restarting them.
        """
        logger.debug("Starting run() method for thread %s"
                     % threading.current_thread().name)
        logger.debug("Shutting down for refresh from %s."
                     % threading.current_thread().name)
        try:
            wx.CallAfter(BeginBusyCursorIfRequired)
            app = wx.GetApp()
            app.GetScheduleController().ApplySchedule(event)
            event.foldersController.ShutDownUploadThreads()
            shutdownForRefreshCompleteEvent = \
                MYDATA_EVENTS.ShutdownForRefreshCompleteEvent(
                    shutdownSuccessful=True)
            PostEvent(shutdownForRefreshCompleteEvent)
            wx.CallAfter(EndBusyCursorIfRequired, event)
        except:
            message = "An error occurred while trying to shut down " \
                "the existing data-scan-and-upload process in order " \
                "to start another one.\n\n" \
                "See the Log tab for details of the error."
            logger.error(message)

            def ShowDialog():
                """
                Show error dialog in main thread.
                """
                dlg = wx.MessageDialog(None, message, "MyData",
                                       wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
            wx.CallAfter(ShowDialog)
        logger.debug("Finishing run() method for thread %s"
                     % threading.current_thread().name)

    shutdownForRefreshThread = \
        threading.Thread(target=ShutdownForRefreshWorker,
                         name="ShutdownForRefreshThread")
    MYDATA_THREADS.Add(shutdownForRefreshThread)
    logger.debug("Starting thread %s" % shutdownForRefreshThread.name)
    shutdownForRefreshThread.start()
    logger.debug("Started thread %s" % shutdownForRefreshThread.name)


def ShutdownForRefreshComplete(event):
    """
    Respond to completion of shutdown for refresh.
    """
    wx.GetApp().OnRefresh(event)


def CheckConnectivity(event):
    """
    Checks network connectivity.
    """

    def CheckConnectivityWorker():
        """
        Checks network connectivity in separate thread.
        """
        wx.CallAfter(BeginBusyCursorIfRequired)
        try:
            activeNetworkInterfaces = \
                UploaderModel.GetActiveNetworkInterfaces()
        except Exception as err:
            logger.error(traceback.format_exc())
            if type(err).__name__ == "WindowsError" and \
                    "The handle is invalid" in str(err):
                message = "An error occurred, suggesting " \
                    "that you have launched MyData.exe from a " \
                    "Command Prompt window.  Please launch it " \
                    "from a shortcut or from a Windows Explorer " \
                    "window instead.\n" \
                    "\n" \
                    "See: https://bugs.python.org/issue3905"

                def ShowErrorDialog(message):
                    """
                    Show error dialog in main thread.
                    """
                    dlg = wx.MessageDialog(None, message, "MyData",
                                           wx.OK | wx.ICON_ERROR)
                    dlg.ShowModal()
                wx.CallAfter(ShowErrorDialog, message)
                return
            else:
                raise
        wx.CallAfter(EndBusyCursorIfRequired, event)
        if len(activeNetworkInterfaces) > 0:
            logger.debug("Found at least one active network interface: %s."
                         % activeNetworkInterfaces[0])
            app = wx.GetApp()
            # An app created by mydata/tests/test*.py might be just a
            # vanilla wx.App(), not a full MyData app instance.
            if hasattr(app, "GetMainFrame"):
                app.SetLastConnectivityCheckSuccess(True)
                app.SetLastConnectivityCheckTime(datetime.now())
                app.SetActiveNetworkInterface(activeNetworkInterfaces[0])
            if hasattr(event, "nextEvent") and event.nextEvent:
                PostEvent(event.nextEvent)
        else:
            wx.GetApp().SetLastConnectivityCheckSuccess(False)
            wx.GetApp().SetLastConnectivityCheckTime(datetime.now())
            wx.GetApp().SetActiveNetworkInterface(None)
            ReportNoActiveInterfaces()

    if wx.PyApp.IsMainLoopRunning():
        checkConnectivityThread = \
            threading.Thread(target=CheckConnectivityWorker,
                             name="CheckConnectivityThread")
        MYDATA_THREADS.Add(checkConnectivityThread)
        checkConnectivityThread.start()
    else:
        CheckConnectivityWorker()


def InstrumentNameMismatch(event):
    """
    Responds to instrument name mismatch in Settings dialog.
    """
    message = "A previous instrument name of \"%s\" " \
        "has been associated with this MyData instance.\n" \
        "Please choose how you would like the new \"%s\" " \
        "instrument name to be applied." \
        % (event.oldInstrumentName, event.newInstrumentName)
    renameChoice = "Rename the existing instrument record to " \
        "\"%s\"." % event.newInstrumentName
    discardChoice = "Discard the new instrument name and revert " \
        "to \"%s\"." % event.oldInstrumentName
    createChoice = "Use a separate instrument record for \"%s\", " \
        "creating it if necessary." \
        % event.newInstrumentName
    dlg = wx.SingleChoiceDialog(event.settingsDialog, message,
                                "MyData - Instrument Name Changed",
                                [renameChoice, discardChoice,
                                 createChoice], wx.CHOICEDLG_STYLE)
    if dlg.ShowModal() == wx.ID_OK:
        if dlg.GetStringSelection() == renameChoice:
            logger.info("OK, we will rename the "
                        "existing instrument record.")
            settingsDialogValidationEvent = \
                MYDATA_EVENTS.SettingsDialogValidationEvent(
                    settingsDialog=event.settingsDialog,
                    settingsModel=event.settingsModel)
            renameInstrumentEvent = MYDATA_EVENTS.RenameInstrumentEvent(
                settingsDialog=event.settingsDialog,
                settingsModel=event.settingsModel,
                facilityName=event.settingsDialog.GetFacilityName(),
                oldInstrumentName=event.oldInstrumentName,
                newInstrumentName=event.newInstrumentName,
                nextEvent=settingsDialogValidationEvent)
            PostEvent(renameInstrumentEvent)
            return
        elif dlg.GetStringSelection() == discardChoice:
            logger.info("OK, we will discard the new instrument name.")
            event.settingsDialog.SetInstrumentName(
                event.settingsModel.general.instrumentName)
            event.settingsDialog.instrumentNameField.SetFocus()
            event.settingsDialog.instrumentNameField.SelectAll()
        elif dlg.GetStringSelection() == createChoice:
            logger.info("OK, we will create a new instrument record.")
            settingsDialogValidationEvent = \
                MYDATA_EVENTS.SettingsDialogValidationEvent(
                    settingsDialog=event.settingsDialog,
                    settingsModel=event.settingsModel)
            intervalSinceLastCheck = \
                datetime.now() - \
                wx.GetApp().GetLastConnectivityCheckTime()
            checkInterval = event.settingsModel.connectivityCheckInterval
            if intervalSinceLastCheck.total_seconds() >= checkInterval \
                    or not wx.GetApp()\
                    .GetLastConnectivityCheckSuccess():
                checkConnectivityEvent = \
                    MYDATA_EVENTS.CheckConnectivityEvent(
                        settingsModel=event.settingsModel,
                        nextEvent=settingsDialogValidationEvent)
                PostEvent(checkConnectivityEvent)
            else:
                PostEvent(settingsDialogValidationEvent)


def RenameInstrument(event):
    """
    Responds to instrument rename request from Settings dialog.
    """

    def RenameInstrumentWorker():
        """
        Renames instrument in separate thread.
        """
        logger.debug("Starting run() method for thread %s"
                     % threading.current_thread().name)
        try:
            wx.CallAfter(BeginBusyCursorIfRequired)
            event.settingsModel.RenameInstrument(
                event.facilityName,
                event.oldInstrumentName,
                event.newInstrumentName)

            wx.CallAfter(EndBusyCursorIfRequired, event)
            if hasattr(event, "nextEvent") and event.nextEvent:
                PostEvent(event.nextEvent)
        except DuplicateKey:
            wx.CallAfter(EndBusyCursorIfRequired, event)

            def NotifyUserOfDuplicateInstrumentName():
                """
                Notifies user of duplicate instrument name.
                """
                message = "Instrument name \"%s\" already exists in " \
                    "facility \"%s\"." \
                    % (event.newInstrumentName,
                       event.facilityName)
                dlg = wx.MessageDialog(None, message, "MyData",
                                       wx.OK | wx.ICON_ERROR)
                if wx.PyApp.IsMainLoopRunning():
                    dlg.ShowModal()
                event.settingsDialog.instrumentNameField.SetFocus()
                event.settingsDialog.instrumentNameField.SelectAll()
                if not wx.PyApp.IsMainLoopRunning():
                    raise DuplicateKey(message)
            if wx.PyApp.IsMainLoopRunning():
                wx.CallAfter(NotifyUserOfDuplicateInstrumentName)
            else:
                NotifyUserOfDuplicateInstrumentName()
        logger.debug("Finishing run() method for thread %s"
                     % threading.current_thread().name)

    if wx.PyApp.IsMainLoopRunning():
        renameInstrumentThread = \
            threading.Thread(target=RenameInstrumentWorker,
                             name="RenameInstrumentThread")
        MYDATA_THREADS.Add(renameInstrumentThread)
        logger.debug("Starting thread %s" % renameInstrumentThread.name)
        renameInstrumentThread.start()
        logger.debug("Started thread %s" % renameInstrumentThread.name)
    else:
        RenameInstrumentWorker()


def SettingsDialogValidation(event):
    """
    Handles settings validation request from Settings dialog.
    """

    def ValidateWorker(settingsModel):
        """
        Performs settings validation in separate thread.
        """
        logger.debug("Starting run() method for thread %s"
                     % threading.current_thread().name)
        try:
            wx.CallAfter(BeginBusyCursorIfRequired, event)
            wx.CallAfter(event.settingsDialog.okButton.Disable)
            wx.CallAfter(event.settingsDialog.lockOrUnlockButton.Disable)

            app = wx.GetApp()
            if hasattr(app, "GetLastConnectivityCheckTime"):
                intervalSinceLastCheck = datetime.now() - \
                    app.GetLastConnectivityCheckTime()
                checkInterval = event.settingsModel.connectivityCheckInterval
                if intervalSinceLastCheck.total_seconds() >= checkInterval \
                        or not app.GetLastConnectivityCheckSuccess():
                    settingsDialogValidationEvent = \
                        MYDATA_EVENTS.SettingsDialogValidationEvent(
                            settingsDialog=event.settingsDialog,
                            settingsModel=settingsModel,
                            okEvent=event)
                    checkConnectivityEvent = \
                        MYDATA_EVENTS.CheckConnectivityEvent(
                            settingsDialog=event.settingsDialog,
                            settingsModel=settingsModel,
                            nextEvent=settingsDialogValidationEvent)
                    PostEvent(checkConnectivityEvent)
                    return
            try:
                SaveFieldsFromDialog(event.settingsModel, event.settingsDialog,
                                     saveToDisk=False)
            except:
                logger.error(traceback.format_exc())

            def SetStatusMessage(message):
                """
                Updates status bar.
                """
                if hasattr(app, "GetMainFrame"):
                    wx.CallAfter(
                        wx.GetApp().GetMainFrame().SetStatusMessage, message)
            try:
                datasetCount = ValidateSettings(settingsModel, SetStatusMessage)
                PostEvent(MYDATA_EVENTS.ProvideSettingsValidationResultsEvent(
                    settingsDialog=event.settingsDialog,
                    settingsModel=event.settingsModel,
                    datasetCount=datasetCount))
            except UserAbortedSettingsValidation:
                event.settingsModel.RollBack()
                return
            except InvalidSettings as invalidSettings:
                PostEvent(MYDATA_EVENTS.ProvideSettingsValidationResultsEvent(
                    settingsDialog=event.settingsDialog,
                    settingsModel=event.settingsModel,
                    invalidSettings=invalidSettings))
            finally:
                wx.CallAfter(EndBusyCursorIfRequired, event)
                if wx.version().startswith("3.0.3.dev"):
                    arrowCursor = wx.Cursor(wx.CURSOR_ARROW)
                else:
                    arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
                event.settingsDialog.dialogPanel.SetCursor(arrowCursor)
        finally:
            wx.CallAfter(event.settingsDialog.okButton.Enable)
            wx.CallAfter(event.settingsDialog.lockOrUnlockButton.Enable)
            wx.CallAfter(EndBusyCursorIfRequired, event)

        logger.debug("Finishing run() method for thread %s"
                     % threading.current_thread().name)

    if wx.PyApp.IsMainLoopRunning():
        thread = threading.Thread(target=ValidateWorker,
                                  args=(event.settingsModel,),
                                  name="SettingsModelValidationThread")
        logger.debug("Starting thread %s" % thread.name)
        thread.start()
        logger.debug("Started thread %s" % thread.name)
    else:
        ValidateWorker(event.settingsModel)


def ProvideSettingsValidationResults(event):
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    # Needs refactoring.
    """
    Only called after settings dialog has been shown.
    Not called if settings validation was triggered by
    a background task.
    """
    invalidSettings = getattr(event, "invalidSettings", None)
    if invalidSettings:
        message = invalidSettings.message
        logger.error(message)
        app = wx.GetApp()
        if hasattr(app, "GetMainFrame"):
            app.GetMainFrame().SetStatusMessage("")

        if invalidSettings.suggestion:
            currentValue = ""
            if invalidSettings.field == "facility_name":
                currentValue = event.settingsDialog.GetFacilityName()
            elif invalidSettings.field == "mytardis_url":
                currentValue = event.settingsDialog.GetMyTardisUrl()
            message = message.strip()
            if currentValue != "":
                message += "\n\nMyData suggests that you replace \"%s\" " \
                    % currentValue
                message += "with \"%s\"." \
                    % invalidSettings.suggestion
            else:
                message += "\n\nMyData suggests that you use \"%s\"." \
                    % invalidSettings.suggestion
            dlg = wx.MessageDialog(None, message, "MyData",
                                   wx.OK | wx.CANCEL | wx.ICON_ERROR)
            if wx.PyApp.IsMainLoopRunning():
                okToUseSuggestion = dlg.ShowModal()
            else:
                sys.stderr.write("%s\n" % message)
                sys.stderr.write("Assuming it's OK to use suggestion.\n")
                okToUseSuggestion = wx.ID_OK
            if okToUseSuggestion == wx.ID_OK:
                if invalidSettings.field == "facility_name":
                    event.settingsDialog.SetFacilityName(
                        invalidSettings.suggestion)
                elif invalidSettings.field == "mytardis_url":
                    event.settingsDialog.SetMyTardisUrl(
                        invalidSettings.suggestion)
        else:
            dlg = wx.MessageDialog(None, message, "MyData",
                                   wx.OK | wx.ICON_ERROR)
            if wx.PyApp.IsMainLoopRunning():
                dlg.ShowModal()
            else:
                sys.stderr.write("%s\n" % message)
        if invalidSettings.field == "instrument_name":
            event.settingsDialog.instrumentNameField.SetFocus()
            event.settingsDialog.instrumentNameField.SelectAll()
        elif invalidSettings.field == "facility_name":
            event.settingsDialog.facilityNameField.SetFocus()
            event.settingsDialog.facilityNameField.SelectAll()
        elif invalidSettings.field == "data_directory":
            event.settingsDialog.dataDirectoryField.SetFocus()
            event.settingsDialog.dataDirectoryField.SelectAll()
        elif invalidSettings.field == "mytardis_url":
            event.settingsDialog.myTardisUrlField.SetFocus()
            event.settingsDialog.myTardisUrlField.SelectAll()
        elif invalidSettings.field == "contact_name":
            event.settingsDialog.contactNameField.SetFocus()
            event.settingsDialog.contactNameField.SelectAll()
        elif invalidSettings.field == "contact_email":
            event.settingsDialog.contactEmailField.SetFocus()
            event.settingsDialog.contactEmailField.SelectAll()
        elif invalidSettings.field == "username":
            event.settingsDialog.usernameField.SetFocus()
            event.settingsDialog.usernameField.SelectAll()
        elif invalidSettings.field == "api_key":
            event.settingsDialog.apiKeyField.SetFocus()
            event.settingsDialog.apiKeyField.SelectAll()
        elif invalidSettings.field == "scheduled_time":
            event.settingsDialog.timeCtrl.SetFocus()
        elif invalidSettings.field == "includes_file":
            event.settingsDialog.includesFileField.SetFocus()
            event.settingsDialog.includesFileField.SelectAll()
        elif invalidSettings.field == "excludes_file":
            event.settingsDialog.excludesFileField.SetFocus()
            event.settingsDialog.excludesFileField.SelectAll()
        logger.debug("Settings were not valid, so Settings dialog "
                     "should remain visible.")
        if wx.version().startswith("3.0.3.dev"):
            arrowCursor = wx.Cursor(wx.CURSOR_ARROW)
        else:
            arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
        event.settingsDialog.dialogPanel.SetCursor(arrowCursor)
        event.settingsModel.RollBack()
        return

    if event.settingsModel.filters.ignoreOldDatasets:
        intervalIfUsed = " (created within the past %d %s)" \
            % (event.settingsModel.filters.ignoreOldDatasetIntervalNumber,
               event.settingsModel.filters.ignoreOldDatasetIntervalUnit)
    else:
        intervalIfUsed = ""
    numDatasets = getattr(event, "datasetCount", None)
    if numDatasets and numDatasets != -1:
        message = "Assuming a folder structure of '%s', " \
            "there %s %d %s in \"%s\"%s.\n\n" \
            "Do you want to continue?" \
            % (event.settingsModel.advanced.folderStructure,
               "are" if numDatasets != 1 else "is", numDatasets,
               "datasets" if numDatasets != 1 else "dataset",
               event.settingsDialog.GetDataDirectory(),
               intervalIfUsed)
        if wx.PyApp.IsMainLoopRunning():
            confirmationDialog = \
                wx.MessageDialog(None, message, "MyData",
                                 wx.YES | wx.NO | wx.ICON_QUESTION)
            okToContinue = confirmationDialog.ShowModal()
            if okToContinue != wx.ID_YES:
                return
        else:
            sys.stderr.write("\n%s\n" % message)

    logger.debug("Settings were valid, so we'll save the settings "
                 "to disk and close the Settings dialog.")
    try:
        uploaderModel = UploaderModel(event.settingsModel)
        event.settingsModel.uploaderModel = uploaderModel

        # Use the config path determined by appdirs, not the one
        # determined by a user dragging and dropping a config
        # file onto MyData's Settings dialog:
        app = wx.GetApp()
        if hasattr(app, "GetConfigPath"):
            configPath = app.GetConfigPath()
        else:
            configPath = None
        SaveFieldsFromDialog(event.settingsModel, event.settingsDialog,
                             configPath=configPath, saveToDisk=True)
        if wx.PyApp.IsMainLoopRunning():
            event.settingsDialog.EndModal(wx.ID_OK)
        event.settingsDialog.Show(False)
        logger.debug("Closed Settings dialog.")

        if event.settingsModel.schedule.scheduleType == "Manually":
            message = \
                 "MyData's schedule type is currently " \
                 "set to 'manual', so you will need to click " \
                 "the Upload toolbar icon or the Sync Now " \
                 "menu item to begin the data scans and uploads."
            if wx.PyApp.IsMainLoopRunning():
                title = "Manual Schedule"
                dlg = wx.MessageDialog(None, message, title,
                                       wx.OK | wx.ICON_WARNING)
                dlg.ShowModal()
            else:
                logger.warning(message)
    except:
        logger.error(traceback.format_exc())


def ValidateSettingsForRefresh(event):
    """
    Call MyDataApp's OnRefresh (again) to trigger settings validation.
    """
    wx.GetApp().OnRefresh(event)


def SettingsValidationForRefreshComplete(event):
    """
    Call MyDataApp's OnRefresh (again) to proceed with starting up the
    data folder scans once the settings validation has been completed.
    """
    event.needToValidateSettings = False
    wx.GetApp().OnRefresh(event)


def StartDataUploadsForFolder(event):
    """
    Start the data uploads.
    """
    app = wx.GetApp()
    if hasattr(app, "ShouldAbort") and app.ShouldAbort():
        return

    def StartDataUploadsForFolderWorker():
        """
        Start the data uploads in a dedicated thread.
        """
        logger.debug("Starting run() method for thread %s"
                     % threading.current_thread().name)
        logger.debug("StartDataUploadsForFolderWorker")
        wx.CallAfter(BeginBusyCursorIfRequired)
        message = "Checking for data files on MyTardis and uploading " \
            "if necessary for folder: %s" % event.folderModel.GetFolder()
        logger.info(message)
        app = wx.GetApp()
        if hasattr(app, "TestRunRunning") and app.TestRunRunning():
            logger.testrun(message)
        if type(app).__name__ == "MyData":
            app.DisableTestAndUploadToolbarButtons()
            app.SetPerformingLookupsAndUploads(True)
            app.foldersController.StartUploadsForFolder(
                event.folderModel)
            wx.CallAfter(EndBusyCursorIfRequired, event)

    if wx.PyApp.IsMainLoopRunning():
        startDataUploadsForFolderThread = \
            threading.Thread(target=StartDataUploadsForFolderWorker)
        threadName = startDataUploadsForFolderThread.name
        threadName = \
            threadName.replace("Thread", "StartDataUploadsForFolderThread")
        startDataUploadsForFolderThread.name = threadName
        MYDATA_THREADS.Add(startDataUploadsForFolderThread)
        startDataUploadsForFolderThread.start()
    else:
        StartDataUploadsForFolderWorker()

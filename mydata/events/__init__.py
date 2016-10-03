"""
Custom events for MyData.
"""
import threading
import os
from datetime import datetime
import traceback
import sys
import wx

from mydata.models.settings import SettingsModel
from mydata.models.uploader import UploaderModel
from mydata.utils.exceptions import NoActiveNetworkInterface
from mydata.utils.exceptions import IncompatibleMyTardisVersion
from mydata.utils.exceptions import DuplicateKey
from mydata.logs import logger

MYDATA_EVENT_TYPE = wx.NewEventType()
MYDATA_EVENT_BINDER = wx.PyEventBinder(MYDATA_EVENT_TYPE, 1)

EVT_SHUTDOWN_FOR_REFRESH = wx.NewId()
EVT_SHUTDOWN_FOR_REFRESH_COMPLETE = wx.NewId()
EVT_VALIDATE_SETTINGS_FOR_REFRESH = wx.NewId()
EVT_CHECK_CONNECTIVITY = wx.NewId()
EVT_INSTRUMENT_NAME_MISMATCH = wx.NewId()
EVT_RENAME_INSTRUMENT = wx.NewId()
EVT_SETTINGS_DIALOG_VALIDATION = wx.NewId()
EVT_PROVIDE_SETTINGS_VALIDATION_RESULTS = wx.NewId()
EVT_SETTINGS_VALIDATION_FOR_REFRESH_COMPLETE = wx.NewId()
EVT_START_UPLOADS_FOR_FOLDER = wx.NewId()


def EndBusyCursorIfRequired(event):
    """
    The built in wx.EndBusyCursor raises an ugly exception if the
    busy cursor has already been stopped.
    """
    # pylint: disable=no-member
    # Otherwise pylint complains about PyAssertionError.
    # pylint: disable=protected-access
    try:
        wx.EndBusyCursor()
        if event.settingsDialog:
            if wx.version().startswith("3.0.3.dev"):
                arrowCursor = wx.Cursor(wx.CURSOR_ARROW)
            else:
                arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
            event.settingsDialog.dialogPanel.SetCursor(arrowCursor)
    except wx._core.PyAssertionError, err:
        if "no matching wxBeginBusyCursor()" not in str(err):
            logger.error(str(err))
            raise
    except RuntimeError, err:
        if "wrapped C/C++ object of type MyDataEvent has been deleted" \
                not in str(err):
            logger.error(str(err))
            raise


class MyDataEvents(object):
    """
    Custom events for MyData.
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, notifyWindow):
        self.notifyWindow = notifyWindow
        notifyWindow.Bind(MYDATA_EVENT_BINDER,
                          MyDataEvent.ShutdownForRefresh)
        notifyWindow.Bind(MYDATA_EVENT_BINDER,
                          MyDataEvent.ShutdownForRefreshComplete)
        notifyWindow.Bind(MYDATA_EVENT_BINDER,
                          MyDataEvent.ValidateSettingsForRefresh)
        notifyWindow.Bind(MYDATA_EVENT_BINDER,
                          MyDataEvent.CheckConnectivity)
        notifyWindow.Bind(MYDATA_EVENT_BINDER,
                          MyDataEvent.InstrumentNameMismatch)
        notifyWindow.Bind(MYDATA_EVENT_BINDER,
                          MyDataEvent.RenameInstrument)
        notifyWindow.Bind(MYDATA_EVENT_BINDER,
                          MyDataEvent.SettingsDialogValidation)
        notifyWindow.Bind(MYDATA_EVENT_BINDER,
                          MyDataEvent.ProvideSettingsValidationResults)
        notifyWindow.Bind(MYDATA_EVENT_BINDER,
                          MyDataEvent.SettingsValidationForRefreshComplete)
        notifyWindow.Bind(MYDATA_EVENT_BINDER,
                          MyDataEvent.StartDataUploads)

    def GetNotifyWindow(self):
        """
        Returns the wx.Frame which propagates events,
        which is MyData's main frame..
        """
        return self.notifyWindow


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
            print "\tJoined " + thread.name

MYDATA_THREADS = MyDataThreads()


class MyDataEvent(wx.PyCommandEvent):
    """
    Custom event class for MyData.
    """
    def __init__(self, eventId, **kwargs):
        wx.PyCommandEvent.__init__(self, MYDATA_EVENT_TYPE, eventId)
        self.eventId = eventId
        # Optional event attributes:
        self.settingsModel = None
        self.settingsDialog = None
        self.oldInstrumentName = None
        self.newInstrumentName = None
        self.facilityName = None
        self.nextEvent = None
        for key in kwargs:
            self.__dict__[key] = kwargs[key]

    def GetEventId(self):
        """
        Return event ID.
        """
        return self.eventId

    @staticmethod
    def CheckConnectivity(event):
        """
        Checks network connectivity.
        """
        if event.GetEventId() != EVT_CHECK_CONNECTIVITY:
            event.Skip()
            return

        def CheckConnectivityWorker():
            """
            Checks network connectivity in separate thread.
            """
            wx.CallAfter(wx.BeginBusyCursor)
            # pylint: disable=broad-except
            try:
                activeNetworkInterfaces = \
                    UploaderModel.GetActiveNetworkInterfaces()
            except Exception, err:
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
            wx.CallAfter(EndBusyCursorIfRequired, event)
            if len(activeNetworkInterfaces) > 0:
                logger.debug("Found at least one active network interface: %s."
                             % activeNetworkInterfaces[0])
                app = wx.GetApp()
                if hasattr(app, "GetMainFrame"):
                    app.SetLastConnectivityCheckSuccess(True)
                    app.SetLastConnectivityCheckTime(datetime.now())
                    app.SetActiveNetworkInterface(activeNetworkInterfaces[0])
                if event.nextEvent:
                    wx.PostEvent(wx.GetApp().GetMainFrame(), event.nextEvent)
            else:
                wx.GetApp().SetLastConnectivityCheckSuccess(False)
                wx.GetApp().SetLastConnectivityCheckTime(datetime.now())
                wx.GetApp().SetActiveNetworkInterface(None)
                message = "No active network interfaces." \
                    "\n\n" \
                    "Please ensure that you have an active " \
                    "network interface (e.g. Ethernet or WiFi)."

                def ShowDialog():
                    """
                    Show error dialog in main thread.
                    """
                    dlg = wx.MessageDialog(None, message, "MyData",
                                           wx.OK | wx.ICON_ERROR)
                    dlg.ShowModal()
                    wx.GetApp().GetMainFrame().SetStatusMessage("")
                    wx.GetApp().GetMainFrame().SetConnected(
                        event.settingsModel.GetMyTardisUrl(), False)
                wx.CallAfter(ShowDialog)

        checkConnectivityThread = \
            threading.Thread(target=CheckConnectivityWorker,
                             name="CheckConnectivityThread")
        MYDATA_THREADS.Add(checkConnectivityThread)
        checkConnectivityThread.start()

    @staticmethod
    def InstrumentNameMismatch(event):
        """
        Responds to instrument name mismatch in Settings dialog.
        """
        if event.GetEventId() != EVT_INSTRUMENT_NAME_MISMATCH:
            event.Skip()
            return
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
                    MyDataEvent(EVT_SETTINGS_DIALOG_VALIDATION,
                                settingsDialog=event.settingsDialog,
                                settingsModel=event.settingsModel)
                renameInstrumentEvent = MyDataEvent(
                    EVT_RENAME_INSTRUMENT,
                    settingsDialog=event.settingsDialog,
                    settingsModel=event.settingsModel,
                    facilityName=event.settingsDialog.GetFacilityName(),
                    oldInstrumentName=event.oldInstrumentName,
                    newInstrumentName=event.newInstrumentName,
                    nextEvent=settingsDialogValidationEvent)
                wx.PostEvent(wx.GetApp().GetMainFrame(), renameInstrumentEvent)
                return
            elif dlg.GetStringSelection() == discardChoice:
                logger.info("OK, we will discard the new instrument name.")
                event.settingsDialog.SetInstrumentName(
                    event.settingsModel.GetInstrumentName())
                event.settingsDialog.instrumentNameField.SetFocus()
                event.settingsDialog.instrumentNameField.SelectAll()
            elif dlg.GetStringSelection() == createChoice:
                logger.info("OK, we will create a new instrument record.")
                settingsDialogValidationEvent = \
                    MyDataEvent(EVT_SETTINGS_DIALOG_VALIDATION,
                                settingsDialog=event.settingsDialog,
                                settingsModel=event.settingsModel)
                intervalSinceLastCheck = \
                    datetime.now() - \
                    wx.GetApp().GetLastConnectivityCheckTime()
                checkInterval = \
                    event.settingsModel.GetConnectivityCheckInterval()
                if intervalSinceLastCheck.total_seconds() >= checkInterval \
                        or not wx.GetApp()\
                        .GetLastConnectivityCheckSuccess():
                    checkConnectivityEvent = \
                        MyDataEvent(EVT_CHECK_CONNECTIVITY,
                                    settingsModel=event.settingsModel,
                                    nextEvent=settingsDialogValidationEvent)
                    wx.PostEvent(wx.GetApp().GetMainFrame(),
                                 checkConnectivityEvent)
                else:
                    wx.PostEvent(wx.GetApp().GetMainFrame(),
                                 settingsDialogValidationEvent)

    @staticmethod
    def RenameInstrument(event):
        """
        Responds to instrument rename request from Settings dialog.
        """
        if event.GetEventId() != EVT_RENAME_INSTRUMENT:
            event.Skip()
            return

        def RenameInstrumentWorker():
            """
            Renames instrument in separate thread.
            """
            logger.debug("Starting run() method for thread %s"
                         % threading.current_thread().name)
            try:
                wx.CallAfter(wx.BeginBusyCursor)
                event.settingsModel.RenameInstrument(
                    event.facilityName,
                    event.oldInstrumentName,
                    event.newInstrumentName)

                wx.CallAfter(EndBusyCursorIfRequired, event)
                if event.nextEvent:
                    wx.PostEvent(wx.GetApp().GetMainFrame(), event.nextEvent)
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
                    dlg.ShowModal()
                    event.settingsDialog.instrumentNameField.SetFocus()
                    event.settingsDialog.instrumentNameField.SelectAll()
                wx.CallAfter(NotifyUserOfDuplicateInstrumentName)
            logger.debug("Finishing run() method for thread %s"
                         % threading.current_thread().name)

        renameInstrumentThread = \
            threading.Thread(target=RenameInstrumentWorker,
                             name="RenameInstrumentThread")
        MYDATA_THREADS.Add(renameInstrumentThread)
        logger.debug("Starting thread %s" % renameInstrumentThread.name)
        renameInstrumentThread.start()
        logger.debug("Started thread %s" % renameInstrumentThread.name)

    @staticmethod
    def SettingsDialogValidation(event):
        """
        Handles settings validation request from Settings dialog.
        """
        if event.GetEventId() != EVT_SETTINGS_DIALOG_VALIDATION:
            event.Skip()
            return

        def Validate(settingsModel):
            """
            Performs settings validation in separate thread.
            """
            logger.debug("Starting run() method for thread %s"
                         % threading.current_thread().name)
            try:
                wx.CallAfter(wx.BeginBusyCursor)
                if sys.platform.startswith("win"):
                    # BeginBusyCursor should update the cursor everywhere,
                    # but it doesn't always work on Windows.
                    if wx.version().startswith("3.0.3.dev"):
                        busyCursor = wx.Cursor(wx.CURSOR_WAIT)
                    else:
                        busyCursor = wx.StockCursor(wx.CURSOR_WAIT)
                    wx.CallAfter(event.settingsDialog.dialogPanel.SetCursor,
                                 busyCursor)
                wx.CallAfter(event.settingsDialog.okButton.Disable)
                wx.CallAfter(event.settingsDialog.lockOrUnlockButton.Disable)

                app = wx.GetApp()
                if hasattr(app, "GetLastConnectivityCheckTime"):
                    intervalSinceLastCheck = datetime.now() - \
                        app.GetLastConnectivityCheckTime()
                    checkInterval = \
                        event.settingsModel.GetConnectivityCheckInterval()
                    if intervalSinceLastCheck.total_seconds() >= checkInterval \
                            or not app.GetLastConnectivityCheckSuccess():
                        settingsDialogValidationEvent = \
                            MyDataEvent(EVT_SETTINGS_DIALOG_VALIDATION,
                                        settingsDialog=event.settingsDialog,
                                        settingsModel=settingsModel,
                                        okEvent=event)
                        checkConnectivityEvent = \
                            MyDataEvent(EVT_CHECK_CONNECTIVITY,
                                        settingsDialog=event.settingsDialog,
                                        settingsModel=settingsModel,
                                        nextEvent=settingsDialogValidationEvent)
                        wx.PostEvent(app.GetMainFrame(),
                                     checkConnectivityEvent)
                        return
                try:
                    event.settingsModel.SaveFieldsFromDialog(event.settingsDialog,
                                                             saveToDisk=False)
                except:  # pylint: disable=bare-except
                    logger.error(traceback.format_exc())

                def SetStatusMessage(message):
                    """
                    Updates status bar.
                    """
                    wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage,
                                 message)
                settingsModel.Validate(SetStatusMessage)
                wx.CallAfter(EndBusyCursorIfRequired, event)
                if settingsModel.IsIncompatibleMyTardisVersion():
                    wx.CallAfter(event.settingsDialog.okButton.Enable)
                    wx.CallAfter(event.settingsDialog.lockOrUnlockButton.Enable)
                    return
                provideValidationResultsEvent = MyDataEvent(
                    EVT_PROVIDE_SETTINGS_VALIDATION_RESULTS,
                    settingsDialog=event.settingsDialog,
                    settingsModel=event.settingsModel)
                if hasattr(app, "GetMainFrame"):
                    wx.PostEvent(app.GetMainFrame(),
                                 provideValidationResultsEvent)
            except IncompatibleMyTardisVersion as err:
                wx.CallAfter(EndBusyCursorIfRequired, event)

                def ShowDialog(message):
                    """
                    Show error dialog in main thread.
                    """
                    logger.error(message)
                    # pylint: disable=no-member
                    # Otherwise pylint complains about PyAssertionError.
                    # pylint: disable=protected-access
                    try:
                        wx.EndBusyCursor()
                        if wx.version().startswith("3.0.3.dev"):
                            arrowCursor = wx.Cursor(wx.CURSOR_ARROW)
                        else:
                            arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
                        event.settingsDialog.dialogPanel.SetCursor(arrowCursor)
                    except wx._core.PyAssertionError, err:
                        if "no matching wxBeginBusyCursor()" \
                                not in str(err):
                            logger.error(str(err))
                            raise
                    dlg = wx.MessageDialog(None, message, "MyData",
                                           wx.OK | wx.ICON_ERROR)
                    dlg.ShowModal()
                message = str(err)
                wx.CallAfter(ShowDialog, message)
            finally:
                wx.CallAfter(event.settingsDialog.okButton.Enable)
                wx.CallAfter(event.settingsDialog.lockOrUnlockButton.Enable)
                wx.CallAfter(EndBusyCursorIfRequired, event)

            logger.debug("Finishing run() method for thread %s"
                         % threading.current_thread().name)

        thread = threading.Thread(target=Validate,
                                  args=(event.settingsModel,),
                                  name="SettingsModelValidationThread")
        logger.debug("Starting thread %s" % thread.name)
        thread.start()
        logger.debug("Started thread %s" % thread.name)

    @staticmethod
    def ProvideSettingsValidationResults(event):
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        # Needs refactoring.
        """
        Only called after settings dialog has been shown.
        Not called if settings validation was triggered by
        a background task.
        """
        if event.GetEventId() != EVT_PROVIDE_SETTINGS_VALIDATION_RESULTS:
            event.Skip()
            return
        settingsValidation = event.settingsModel.GetValidation()
        if settingsValidation.Aborted():
            wx.CallAfter(EndBusyCursorIfRequired, event)
            if wx.version().startswith("3.0.3.dev"):
                arrowCursor = wx.Cursor(wx.CURSOR_ARROW)
            else:
                arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
            event.settingsDialog.dialogPanel.SetCursor(arrowCursor)
            event.settingsModel.RollBack()
            return
        if settingsValidation is not None and \
                not settingsValidation.IsValid():
            wx.GetApp().GetMainFrame().SetStatusMessage("")
            message = settingsValidation.GetMessage()
            logger.error(message)

            if settingsValidation.GetSuggestion():
                currentValue = ""
                if settingsValidation.GetField() == "instrument_name":
                    currentValue = event.settingsDialog.GetInstrumentName()
                elif settingsValidation.GetField() == "facility_name":
                    currentValue = event.settingsDialog.GetFacilityName()
                elif settingsValidation.GetField() == "mytardis_url":
                    currentValue = event.settingsDialog.GetMyTardisUrl()
                message = message.strip()
                if currentValue != "":
                    message += "\n\nMyData suggests that you replace \"%s\" " \
                        % currentValue
                    message += "with \"%s\"." \
                        % settingsValidation.GetSuggestion()
                else:
                    message += "\n\nMyData suggests that you use \"%s\"." \
                        % settingsValidation.GetSuggestion()
                dlg = wx.MessageDialog(None, message, "MyData",
                                       wx.OK | wx.CANCEL | wx.ICON_ERROR)
                okToUseSuggestion = dlg.ShowModal()
                if okToUseSuggestion == wx.ID_OK:
                    if settingsValidation.GetField() == "instrument_name":
                        event.settingsDialog\
                            .SetInstrumentName(settingsValidation
                                               .GetSuggestion())
                    elif settingsValidation.GetField() == "facility_name":
                        event.settingsDialog.SetFacilityName(settingsValidation
                                                             .GetSuggestion())
                    elif settingsValidation.GetField() == "mytardis_url":
                        event.settingsDialog.SetMyTardisUrl(settingsValidation
                                                            .GetSuggestion())
            else:
                dlg = wx.MessageDialog(None, message, "MyData",
                                       wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
            if settingsValidation.GetField() == "instrument_name":
                event.settingsDialog.instrumentNameField.SetFocus()
                event.settingsDialog.instrumentNameField.SelectAll()
            elif settingsValidation.GetField() == "facility_name":
                event.settingsDialog.facilityNameField.SetFocus()
                event.settingsDialog.facilityNameField.SelectAll()
            elif settingsValidation.GetField() == "data_directory":
                event.settingsDialog.dataDirectoryField.SetFocus()
                event.settingsDialog.dataDirectoryField.SelectAll()
            elif settingsValidation.GetField() == "mytardis_url":
                event.settingsDialog.myTardisUrlField.SetFocus()
                event.settingsDialog.myTardisUrlField.SelectAll()
            elif settingsValidation.GetField() == "contact_name":
                event.settingsDialog.contactNameField.SetFocus()
                event.settingsDialog.contactNameField.SelectAll()
            elif settingsValidation.GetField() == "contact_email":
                event.settingsDialog.contactEmailField.SetFocus()
                event.settingsDialog.contactEmailField.SelectAll()
            elif settingsValidation.GetField() == "username":
                event.settingsDialog.usernameField.SetFocus()
                event.settingsDialog.usernameField.SelectAll()
            elif settingsValidation.GetField() == "api_key":
                event.settingsDialog.apiKeyField.SetFocus()
                event.settingsDialog.apiKeyField.SelectAll()
            elif settingsValidation.GetField() == "scheduled_time":
                event.settingsDialog.timeCtrl.SetFocus()
            elif settingsValidation.GetField() == "includes_file":
                event.settingsDialog.includesFileField.SetFocus()
                event.settingsDialog.includesFileField.SelectAll()
            elif settingsValidation.GetField() == "excludes_file":
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

        if event.settingsModel.IgnoreOldDatasets():
            intervalIfUsed = " (created within the past %d %s)" \
                % (event.settingsModel.GetIgnoreOldDatasetIntervalNumber(),
                   event.settingsModel.GetIgnoreOldDatasetIntervalUnit())
        else:
            intervalIfUsed = ""
        numDatasets = settingsValidation.GetDatasetCount()
        if numDatasets != -1:
            message = "Assuming a folder structure of '%s', " \
                "there %s %d %s in \"%s\"%s.\n\n" \
                "Do you want to continue?" \
                % (event.settingsModel.GetFolderStructure(),
                   "are" if numDatasets != 1 else "is",
                   settingsValidation.GetDatasetCount(),
                   "datasets" if numDatasets != 1 else "dataset",
                   event.settingsDialog.GetDataDirectory(),
                   intervalIfUsed)
            confirmationDialog = \
                wx.MessageDialog(None, message, "MyData",
                                 wx.YES | wx.NO | wx.ICON_QUESTION)
            okToContinue = confirmationDialog.ShowModal()
            if okToContinue != wx.ID_YES:
                return

        logger.debug("Settings were valid, so we'll save the settings "
                     "to disk and close the Settings dialog.")
        # pylint: disable=bare-except
        try:
            # Now is a good time to define the MyData instances's uploader
            # model object, which will generate a UUID if necessary.
            # The UUID will be saved to disk along with the settings from
            # the settings dialog.
            uploaderModel = UploaderModel(event.settingsModel)
            event.settingsModel.SetUploaderModel(uploaderModel)

            # Use the config path determined by appdirs, not the one
            # determined by a user dragging and dropping a config
            # file onto MyData's Settings dialog:
            app = wx.GetApp()
            if hasattr(app, "GetConfigPath"):
                configPath = app.GetConfigPath()
            else:
                configPath = None
            event.settingsModel.SaveFieldsFromDialog(event.settingsDialog,
                                                     configPath=configPath,
                                                     saveToDisk=True)
            event.settingsDialog.EndModal(wx.ID_OK)
            event.settingsDialog.Show(False)
            logger.debug("Closed Settings dialog.")

            if event.settingsModel.GetScheduleType() == "Manually":
                message = \
                     "MyData's schedule type is currently " \
                     "set to 'manual', so you will need to click " \
                     "the Upload toolbar icon or the Sync Now " \
                     "menu item to begin the data scans and uploads."
                title = "Manual Schedule"
                dlg = wx.MessageDialog(None, message, title,
                                       wx.OK | wx.ICON_WARNING)
                dlg.ShowModal()
        except:
            logger.error(traceback.format_exc())

    @staticmethod
    def ShutdownForRefresh(event):
        """
        Shuts down upload threads before restarting them.
        """
        if event.GetEventId() != EVT_SHUTDOWN_FOR_REFRESH:
            event.Skip()
            return

        def ShutdownForRefreshWorker():
            """
            Shuts down upload threads (in dedicated worker thread)
            before restarting them.
            """
            logger.debug("Starting run() method for thread %s"
                         % threading.current_thread().name)
            logger.debug("Shutting down for refresh from %s."
                         % threading.current_thread().name)
            # pylint: disable=bare-except
            try:
                wx.CallAfter(wx.BeginBusyCursor)
                app = wx.GetApp()
                app.GetScheduleController().ApplySchedule(event)
                event.foldersController.ShutDownUploadThreads()
                shutdownForRefreshCompleteEvent = MyDataEvent(
                    EVT_SHUTDOWN_FOR_REFRESH_COMPLETE,
                    shutdownSuccessful=True)
                wx.PostEvent(app.GetMainFrame(),
                             shutdownForRefreshCompleteEvent)
                wx.CallAfter(EndBusyCursorIfRequired, event)
            except:
                logger.error(traceback.format_exc())
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

    @staticmethod
    def ShutdownForRefreshComplete(event):
        """
        Respond to completion of shutdown for refresh.
        """
        if event.GetEventId() != EVT_SHUTDOWN_FOR_REFRESH_COMPLETE:
            event.Skip()
            return
        wx.GetApp().OnRefresh(event)

    @staticmethod
    def ValidateSettingsForRefresh(event):
        """
        Call MyDataApp's OnRefresh (again) to trigger
        settings validation.
        """
        if event.GetEventId() != EVT_VALIDATE_SETTINGS_FOR_REFRESH:
            event.Skip()
            return
        wx.GetApp().OnRefresh(event)

    @staticmethod
    def SettingsValidationForRefreshComplete(event):
        """
        Call MyDataApp's OnRefresh (again) to proceed
        with starting up the data folder scans once
        the settings validation has been completed.
        """
        if event.GetEventId() != EVT_SETTINGS_VALIDATION_FOR_REFRESH_COMPLETE:
            event.Skip()
            return
        wx.GetApp().OnRefresh(event)

    @staticmethod
    def StartDataUploads(event):
        """
        Start the data uploads.
        """
        if event.GetEventId() != EVT_START_UPLOADS_FOR_FOLDER:
            event.Skip()
            return

        def StartDataUploadsWorker():
            """
            Start the data uploads in a dedicated thread.
            """
            logger.debug("Starting run() method for thread %s"
                         % threading.current_thread().name)
            logger.debug("StartDataUploadsWorker")
            wx.CallAfter(wx.BeginBusyCursor)
            message = "Checking for data files on MyTardis and uploading " \
                "if necessary..."
            wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage, message)
            logger.info(message)
            app = wx.GetApp()
            if app.TestRunRunning():
                logger.testrun(message)
            app.DisableTestAndUploadToolbarButtons()
            wx.GetApp().SetPerformingLookupsAndUploads(True)
            app.foldersController.StartUploadsForFolder(
                event.folderModel)
            wx.CallAfter(EndBusyCursorIfRequired, event)

        startDataUploadsForFolderThread = \
            threading.Thread(target=StartDataUploadsWorker,
                             name="StartDataUploadsThread")
        MYDATA_THREADS.Add(startDataUploadsForFolderThread)
        startDataUploadsForFolderThread.start()

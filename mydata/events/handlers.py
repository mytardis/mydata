"""
Event handlers for MyData.
"""
import os
import threading
import traceback
import sys
import wx

from ..settings import SETTINGS
from ..models.settings.serialize import SaveFieldsFromDialog
from ..models.settings.validation import ValidateSettings
from ..models.instrument import InstrumentModel
from ..models.uploader import UploaderModel
from ..utils.connectivity import CONNECTIVITY
from ..utils.exceptions import DuplicateKey
from ..utils.exceptions import UserAbortedSettingsValidation
from ..utils.exceptions import InvalidSettings
from ..utils import BeginBusyCursorIfRequired
from ..utils import EndBusyCursorIfRequired
from ..threads.flags import FLAGS
from ..logs import logger


def ShutdownForRefresh(event):
    """
    Shuts down upload threads before restarting them when
    a scan and upload task is due to start while another
    scan and upload task is already running.
    """
    from . import MYDATA_EVENTS
    from . import PostEvent

    assert threading.current_thread().name == "MainThread"

    logger.debug("Shutting down for refresh from %s."
                 % threading.current_thread().name)
    try:
        wx.CallAfter(BeginBusyCursorIfRequired)
        app = wx.GetApp()
        app.foldersController.ShutDownUploadThreads()
        shutdownForRefreshCompleteEvent = \
            MYDATA_EVENTS.ShutdownForRefreshCompleteEvent(
                shutdownSuccessful=True)
        PostEvent(shutdownForRefreshCompleteEvent)
        wx.CallAfter(EndBusyCursorIfRequired, event)
        app.scheduleController.ApplySchedule(event)
    except:
        message = "An error occurred while trying to shut down " \
            "the existing data-scan-and-upload process in order " \
            "to start another one.\n\n" \
            "See the Log tab for details of the error."
        logger.error(message)
        logger.error(traceback.format_exc())

        def ShowDialog():
            """
            Show error dialog in main thread.
            """
            dlg = wx.MessageDialog(None, message, "MyData",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
        if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ:
            wx.CallAfter(ShowDialog)


def ShutdownForRefreshComplete(event):
    """
    Respond to completion of shutdown for refresh.
    """
    from .start import StartScansAndUploads
    StartScansAndUploads(event)


def CheckConnectivity(event):
    """
    Checks network connectivity.
    """
    from . import MYDATA_THREADS
    nextEvent = getattr(event, "nextEvent", None)
    if wx.PyApp.IsMainLoopRunning():
        checkConnectivityThread = threading.Thread(
            target=CONNECTIVITY.Check,
            name="CheckConnectivityThread", args=[nextEvent])
        MYDATA_THREADS.Add(checkConnectivityThread)
        checkConnectivityThread.start()
    else:
        CONNECTIVITY.Check(nextEvent)


def InstrumentNameMismatch(event):
    """
    Responds to instrument name mismatch in Settings dialog.
    """
    from . import MYDATA_EVENTS
    from . import PostEvent
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
                    settingsDialog=event.settingsDialog)
            renameInstrumentEvent = MYDATA_EVENTS.RenameInstrumentEvent(
                settingsDialog=event.settingsDialog,
                facilityName=event.settingsDialog.GetFacilityName(),
                oldInstrumentName=event.oldInstrumentName,
                newInstrumentName=event.newInstrumentName,
                nextEvent=settingsDialogValidationEvent)
            PostEvent(renameInstrumentEvent)
            return
        elif dlg.GetStringSelection() == discardChoice:
            logger.info("OK, we will discard the new instrument name.")
            event.settingsDialog.SetInstrumentName(
                SETTINGS.general.instrumentName)
            event.settingsDialog.instrumentNameField.SetFocus()
            event.settingsDialog.instrumentNameField.SelectAll()
        elif dlg.GetStringSelection() == createChoice:
            logger.info("OK, we will create a new instrument record.")
            settingsDialogValidationEvent = \
                MYDATA_EVENTS.SettingsDialogValidationEvent(
                    settingsDialog=event.settingsDialog)
            if CONNECTIVITY.NeedToCheck():
                checkConnectivityEvent = \
                    MYDATA_EVENTS.CheckConnectivityEvent(
                        nextEvent=settingsDialogValidationEvent)
                PostEvent(checkConnectivityEvent)
            else:
                PostEvent(settingsDialogValidationEvent)


def RenameInstrument(event):
    """
    Responds to instrument rename request from Settings dialog.
    """
    from . import PostEvent
    from . import MYDATA_THREADS

    def RenameInstrumentWorker(
            facilityName, oldInstrumentName, newInstrumentName,
            nextEvent, settingsDialog):
        """
        Renames instrument in separate thread.
        """
        logger.debug("Starting run() method for thread %s"
                     % threading.current_thread().name)
        try:
            wx.CallAfter(BeginBusyCursorIfRequired)
            InstrumentModel.RenameInstrument(
                facilityName, oldInstrumentName, newInstrumentName)

            wx.CallAfter(EndBusyCursorIfRequired, event)
            if nextEvent:
                PostEvent(nextEvent)
        except DuplicateKey:
            wx.CallAfter(EndBusyCursorIfRequired, event)

            def NotifyUserOfDuplicateInstrumentName():
                """
                Notifies user of duplicate instrument name.
                """
                message = "Instrument name \"%s\" already exists in " \
                    "facility \"%s\"." \
                    % (newInstrumentName,
                       facilityName)
                dlg = wx.MessageDialog(None, message, "MyData",
                                       wx.OK | wx.ICON_ERROR)
                if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ:
                    dlg.ShowModal()
                settingsDialog.instrumentNameField.SetFocus()
                settingsDialog.instrumentNameField.SelectAll()
                if not wx.PyApp.IsMainLoopRunning():
                    raise DuplicateKey(message)
            if wx.PyApp.IsMainLoopRunning():
                wx.CallAfter(NotifyUserOfDuplicateInstrumentName)
            else:
                NotifyUserOfDuplicateInstrumentName()
        logger.debug("Finishing run() method for thread %s"
                     % threading.current_thread().name)

    # event.Clone() is used below because in wxPython 4 (which we will
    # migrate to soon), the event attributes (e.g. event.newInstrumentName)
    # are deleted when this event handler (RenameInstrument) finishes
    # running, even if the spawned thread is still running.  A better
    # option could be to just pass the required attributes as separate
    # arguments to RenameInstrumentWorker.
    args = [
        event.facilityName, event.oldInstrumentName, event.newInstrumentName,
        getattr(event, "nextEvent", None), event.settingsDialog]
    if wx.PyApp.IsMainLoopRunning():
        renameInstrumentThread = \
            threading.Thread(target=RenameInstrumentWorker,
                             name="RenameInstrumentThread",
                             args=args)
        MYDATA_THREADS.Add(renameInstrumentThread)
        logger.debug("Starting thread %s" % renameInstrumentThread.name)
        renameInstrumentThread.start()
        logger.debug("Started thread %s" % renameInstrumentThread.name)
    else:
        RenameInstrumentWorker(*args)


def SettingsDialogValidation(event):
    """
    Handles settings validation request from Settings dialog.
    """
    from . import MYDATA_EVENTS
    from . import PostEvent

    def ValidateWorker(settingsDialog):
        """
        Performs settings validation in separate thread.
        """
        logger.debug("Starting run() method for thread %s"
                     % threading.current_thread().name)
        try:
            wx.CallAfter(BeginBusyCursorIfRequired, event)
            wx.CallAfter(settingsDialog.okButton.Disable)
            wx.CallAfter(settingsDialog.lockOrUnlockButton.Disable)

            app = wx.GetApp()
            if hasattr(app, "connectivity"):
                if CONNECTIVITY.NeedToCheck():
                    settingsDialogValidationEvent = \
                        MYDATA_EVENTS.SettingsDialogValidationEvent(
                            settingsDialog=settingsDialog,
                            okEvent=event)
                    checkConnectivityEvent = \
                        MYDATA_EVENTS.CheckConnectivityEvent(
                            settingsDialog=settingsDialog,
                            nextEvent=settingsDialogValidationEvent)
                    PostEvent(checkConnectivityEvent)
                    return
            try:
                SaveFieldsFromDialog(settingsDialog, saveToDisk=False)
            except:
                logger.error(traceback.format_exc())

            def SetStatusMessage(message):
                """
                Updates status bar.
                """
                if hasattr(app, "frame"):
                    wx.CallAfter(
                        wx.GetApp().frame.SetStatusMessage, message)
            try:
                datasetCount = ValidateSettings(SetStatusMessage)
                PostEvent(MYDATA_EVENTS.ProvideSettingsValidationResultsEvent(
                    settingsDialog=settingsDialog,
                    datasetCount=datasetCount))
            except UserAbortedSettingsValidation:
                SETTINGS.RollBack()
                return
            except InvalidSettings as invalidSettings:
                PostEvent(MYDATA_EVENTS.ProvideSettingsValidationResultsEvent(
                    settingsDialog=settingsDialog,
                    invalidSettings=invalidSettings))
            finally:
                wx.CallAfter(EndBusyCursorIfRequired, event)
        finally:
            wx.CallAfter(settingsDialog.okButton.Enable)
            wx.CallAfter(settingsDialog.lockOrUnlockButton.Enable)
            wx.CallAfter(EndBusyCursorIfRequired, event)

        logger.debug("Finishing run() method for thread %s"
                     % threading.current_thread().name)

    if wx.PyApp.IsMainLoopRunning():
        thread = threading.Thread(target=ValidateWorker,
                                  name="SettingsModelValidationThread",
                                  args=[event.settingsDialog])
        logger.debug("Starting thread %s" % thread.name)
        thread.start()
        logger.debug("Started thread %s" % thread.name)
    else:
        ValidateWorker(event.settingsDialog)


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
        if hasattr(app, "frame"):
            app.frame.SetStatusMessage("")

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
            if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ:
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
            if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ:
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
        EndBusyCursorIfRequired(event)
        SETTINGS.RollBack()
        return

    if SETTINGS.filters.ignoreOldDatasets:
        intervalIfUsed = " (created within the past %d %s)" \
            % (SETTINGS.filters.ignoreOldDatasetIntervalNumber,
               SETTINGS.filters.ignoreOldDatasetIntervalUnit)
    else:
        intervalIfUsed = ""
    if SETTINGS.filters.ignoreNewDatasets:
        intervalIfUsed += " (older than %d %s)" \
            % (SETTINGS.filters.ignoreNewDatasetIntervalNumber,
               SETTINGS.filters.ignoreNewDatasetIntervalUnit)
    numDatasets = getattr(event, "datasetCount", None)
    if numDatasets is not None and numDatasets != -1:
        filtersSummary = ""
        if SETTINGS.filters.userFilter or \
                SETTINGS.filters.datasetFilter or \
                SETTINGS.filters.experimentFilter:
            filtersSummary = "and applying the specified filters, "

        message = "Assuming a folder structure of '%s', %s" \
            "there %s %d %s in \"%s\"%s.\n\n" \
            "Do you want to continue?" \
            % (SETTINGS.advanced.folderStructure,
               filtersSummary,
               "are" if numDatasets != 1 else "is", numDatasets,
               "datasets" if numDatasets != 1 else "dataset",
               event.settingsDialog.GetDataDirectory(),
               intervalIfUsed)
        confirmationDialog = \
            wx.MessageDialog(None, message, "MyData",
                             wx.YES | wx.NO | wx.ICON_QUESTION)
        if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ:
            okToContinue = confirmationDialog.ShowModal()
            if okToContinue != wx.ID_YES:
                return
        else:
            sys.stderr.write("\n%s\n" % message)

    logger.debug("Settings were valid, so we'll save the settings "
                 "to disk and close the Settings dialog.")
    try:
        uploaderModel = UploaderModel(SETTINGS)
        SETTINGS.uploaderModel = uploaderModel

        # Use the config path determined by appdirs, not the one
        # determined by a user dragging and dropping a config
        # file onto MyData's Settings dialog:
        SaveFieldsFromDialog(event.settingsDialog, saveToDisk=True)
        if wx.PyApp.IsMainLoopRunning():
            event.settingsDialog.EndModal(wx.ID_OK)
        event.settingsDialog.Show(False)
        logger.debug("Closed Settings dialog.")

        if SETTINGS.schedule.scheduleType == "Manually":
            message = \
                 "MyData's schedule type is currently " \
                 "set to 'manual', so you will need to click " \
                 "the Upload toolbar icon or the Sync Now " \
                 "menu item to begin the data scans and uploads."
            title = "Manual Schedule"
            dlg = wx.MessageDialog(None, message, title,
                                   wx.OK | wx.ICON_WARNING)
            if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ:
                dlg.ShowModal()
            else:
                logger.warning(message)
    except:
        logger.error(traceback.format_exc())


def ValidateSettingsForRefresh(event):
    """
    Call StartScansAndUploads (again) to trigger settings validation.
    """
    from .start import StartScansAndUploads
    StartScansAndUploads(event)


def SettingsValidationForRefreshComplete(event):
    """
    Call StartScansAndUploads (again) to proceed with starting up the
    data folder scans once the settings validation has been completed.
    """
    from .start import StartScansAndUploads
    event.needToValidateSettings = False
    StartScansAndUploads(event)


def StartDataUploadsForFolder(event):
    """
    Start the data uploads.
    """
    from . import MYDATA_THREADS
    if FLAGS.shouldAbort or not FLAGS.scanningFolders:
        return

    def StartDataUploadsForFolderWorker(folderModel):
        """
        Start the data uploads in a dedicated thread.
        """
        logger.debug("Starting run() method for thread %s"
                     % threading.current_thread().name)
        logger.debug("StartDataUploadsForFolderWorker")
        wx.CallAfter(BeginBusyCursorIfRequired)
        if FLAGS.shouldAbort or not FLAGS.scanningFolders:
            return
        FLAGS.performingLookupsAndUploads = True
        message = "Checking for data files on MyTardis and uploading " \
            "if necessary for folder: %s" % folderModel.folderName
        logger.info(message)
        app = wx.GetApp()
        if FLAGS.testRunRunning:
            logger.testrun(message)
        if type(app).__name__ == "MyData":
            wx.CallAfter(app.frame.toolbar.DisableTestAndUploadToolbarButtons)
            app.foldersController.StartUploadsForFolder(folderModel)
            wx.CallAfter(EndBusyCursorIfRequired, event)

    if wx.PyApp.IsMainLoopRunning():
        startDataUploadsForFolderThread = \
            threading.Thread(target=StartDataUploadsForFolderWorker,
                             args=[event.folderModel])
        threadName = startDataUploadsForFolderThread.name
        threadName = \
            threadName.replace("Thread", "StartDataUploadsForFolderThread")
        startDataUploadsForFolderThread.name = threadName
        MYDATA_THREADS.Add(startDataUploadsForFolderThread)
        startDataUploadsForFolderThread.start()
    else:
        StartDataUploadsForFolderWorker(event.folderModel)


def DidntFindDatafileOnServer(event):
    """
    Didn't find DataFile on MyTardis server
    """
    wx.GetApp().foldersController.UploadDatafile(event)


def FoundIncompleteStaged(event):
    """
    Found incomplete file on staging
    """
    wx.GetApp().foldersController.UploadDatafile(event)


def FoundVerifiedDatafile(event):
    """
    Found verified file on MyTardis server
    """
    wx.GetApp().foldersController.CountCompletedUploadsAndVerifications(event)


def FoundFullSizeStaged(event):
    """
    Found full-sized file on staging
    """
    wx.GetApp().foldersController.CountCompletedUploadsAndVerifications(event)


def FoundUnverifiedNoDfosDatafile(event):
    """
    Found unverified file without any DataFileObjects (Replicas)
    """
    wx.GetApp().foldersController.CountCompletedUploadsAndVerifications(event)


def FoundUnverifiedUnstaged(event):
    """
    If we're not using staged uploads, we can't retry the upload, because
    the DataFile has already been created and we don't want to trigger
    a Duplicate Key error, so we just need to wait for the file to be
    verified:
    """
    wx.GetApp().foldersController.CountCompletedUploadsAndVerifications(event)


def UploadComplete(event):
    """
    Upload complete
    """
    wx.GetApp().foldersController.CountCompletedUploadsAndVerifications(event)


def UploadFailed(event):
    """
    Upload failed
    """
    wx.GetApp().foldersController.CountCompletedUploadsAndVerifications(event)


def ShutDownUploads(event):
    """
    Shut down uploads
    """
    wx.GetApp().foldersController.ShutDownUploadThreads(event)

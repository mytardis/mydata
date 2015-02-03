import wx
import threading
import os
from datetime import datetime
import traceback
import sys

from SettingsModel import SettingsModel
from UploaderModel import UploaderModel
from Exceptions import NoActiveNetworkInterface
from Exceptions import IncompatibleMyTardisVersion
from Exceptions import DuplicateKey
from logger.Logger import logger

MYDATA_EVENT_TYPE = wx.NewEventType()
MYDATA_EVENT_BINDER = wx.PyEventBinder(MYDATA_EVENT_TYPE, 1)

EVT_SHUTDOWN_FOR_REFRESH = wx.NewId()
EVT_SHUTDOWN_FOR_REFRESH_COMPLETE = wx.NewId()
EVT_SETTINGS_VALIDATION_FOR_REFRESH = wx.NewId()
EVT_CHECK_CONNECTIVITY = wx.NewId()
EVT_INSTRUMENT_NAME_MISMATCH = wx.NewId()
EVT_RENAME_INSTRUMENT = wx.NewId()
EVT_SETTINGS_DIALOG_VALIDATION = wx.NewId()
EVT_PROVIDE_SETTINGS_VALIDATION_RESULTS = wx.NewId()
EVT_SETTINGS_VALIDATION_FOR_REFRESH_COMPLETE = wx.NewId()
EVT_START_DATA_UPLOADS = wx.NewId()


class MyDataEvents():
    def __init__(self, notifyWindow):
        self.notifyWindow = notifyWindow
        notifyWindow.Bind(MYDATA_EVENT_BINDER, MyDataEvent.ShutdownForRefresh)
        notifyWindow.Bind(MYDATA_EVENT_BINDER, MyDataEvent.ShutdownForRefreshComplete)
        notifyWindow.Bind(MYDATA_EVENT_BINDER, MyDataEvent.SettingsValidationForRefresh)
        notifyWindow.Bind(MYDATA_EVENT_BINDER, MyDataEvent.CheckConnectivity)
        notifyWindow.Bind(MYDATA_EVENT_BINDER, MyDataEvent.InstrumentNameMismatch)
        notifyWindow.Bind(MYDATA_EVENT_BINDER, MyDataEvent.RenameInstrument)
        notifyWindow.Bind(MYDATA_EVENT_BINDER, MyDataEvent.SettingsDialogValidation)
        notifyWindow.Bind(MYDATA_EVENT_BINDER, MyDataEvent.ProvideSettingsValidationResults)
        notifyWindow.Bind(MYDATA_EVENT_BINDER, MyDataEvent.SettingsValidationForRefreshComplete)
        notifyWindow.Bind(MYDATA_EVENT_BINDER, MyDataEvent.StartDataUploads)

    def GetNotifyWindow(self):
        return self.notifyWindow


class MyDataThreads():
    def __init__(self):
        self.threads = []

    def __str__(self):
        return str(self.threads)

    def Add(self, thread):
        self.threads.append(thread)

    def Join(self):
        for thread in self.threads:
            thread.join()
            print "\tJoined " + thread.name

myDataThreads = MyDataThreads()


class MyDataEvent(wx.PyCommandEvent):
    def __init__(self, id, **kwargs):
        wx.PyCommandEvent.__init__(self, MYDATA_EVENT_TYPE, id)
        self.id = id
        for key in kwargs:
            self.__dict__[key] = kwargs[key]

    # def Shutdown(event):
        # """ Just for testing - not used in production. """
        # if event.id != EVT_SHUTDOWN:
            # event.Skip()
            # return
        # print "Shutting down..."
        # myDataThreads.Join()
        # print "Exiting..."
        # os._exit(0)

    def CheckConnectivity(event):
        if event.id != EVT_CHECK_CONNECTIVITY:
            event.Skip()
            return
        def checkConnectivityWorker():
            wx.CallAfter(wx.BeginBusyCursor)
            activeNetworkInterfaces = \
                UploaderModel.GetActiveNetworkInterfaces()
            def endBusyCursorIfRequired():
                try:
                    wx.EndBusyCursor()
                except wx._core.PyAssertionError, e:
                    if not "no matching wxBeginBusyCursor()" in str(e):
                        logger.error(str(e))
                        raise
            wx.CallAfter(endBusyCursorIfRequired)
            if len(activeNetworkInterfaces) > 0:
                logger.debug("Found at least one active network interface: %s." \
                    % activeNetworkInterfaces[0])
                wx.GetApp().SetLastNetworkConnectivityCheckSuccess(True)
                wx.GetApp().SetLastNetworkConnectivityCheckTime(datetime.now())
                wx.GetApp().SetActiveNetworkInterface(activeNetworkInterfaces[0])
                if hasattr(event, "nextEvent"):
                    wx.PostEvent(wx.GetApp().GetMainFrame(), event.nextEvent)
            else:
                wx.GetApp().SetLastNetworkConnectivityCheckSuccess(False)
                wx.GetApp().SetLastNetworkConnectivityCheckTime(datetime.now())
                wx.GetApp().SetActiveNetworkInterface(None)
                message = "No active network interfaces." \
                    "\n\n" \
                    "Please ensure that you have an active " \
                    "network interface (e.g. Ethernet or WiFi)."

                def showDialog():
                    dlg = wx.MessageDialog(None, message, "MyData",
                                           wx.OK | wx.ICON_ERROR)
                    dlg.ShowModal()
                    wx.GetApp().GetMainFrame().SetStatusMessage("")
                    wx.GetApp().GetMainFrame().SetConnected(
                        event.settingsModel.GetMyTardisUrl(), False)
                wx.CallAfter(showDialog)

        checkConnectivityThread = \
            threading.Thread(target=checkConnectivityWorker,
                             name="CheckConnectivityThread")
        myDataThreads.Add(checkConnectivityThread)
        checkConnectivityThread.start()

    def InstrumentNameMismatch(event):
        if event.id != EVT_INSTRUMENT_NAME_MISMATCH:
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
                intervalSinceLastConnectivityCheck = \
                    datetime.now() - wx.GetApp().GetLastNetworkConnectivityCheckTime()
                # FIXME: Magic number of 30 seconds since last connectivity check.
                if intervalSinceLastConnectivityCheck.total_seconds() >= 30 or \
                        not wx.GetApp().GetLastNetworkConnectivityCheckSuccess():
                    checkConnectivityEvent = \
                        MyDataEvent(EVT_CHECK_CONNECTIVITY,
                                    settingsModel=event.settingsModel,
                                    nextEvent=settingsDialogValidationEvent)
                    wx.PostEvent(wx.GetApp().GetMainFrame(), checkConnectivityEvent)
                else:
                    wx.PostEvent(wx.GetApp().GetMainFrame(), settingsDialogValidationEvent)

    def RenameInstrument(event):
        if event.id != EVT_RENAME_INSTRUMENT:
            event.Skip()
            return

        def renameInstrumentWorker():
            logger.debug("Starting run() method for thread %s" % threading.current_thread().name)
            try:
                wx.CallAfter(wx.BeginBusyCursor)
                event.settingsModel.RenameInstrument(
                    event.facilityName,
                    event.oldInstrumentName,
                    event.newInstrumentName)
                def endBusyCursorIfRequired():
                    try:
                        wx.EndBusyCursor()
                    except wx._core.PyAssertionError, e:
                        if not "no matching wxBeginBusyCursor()" in str(e):
                            logger.error(str(e))
                            raise
                wx.CallAfter(endBusyCursorIfRequired)
                if hasattr(event, "nextEvent"):
                    wx.PostEvent(wx.GetApp().GetMainFrame(), event.nextEvent)
            except DuplicateKey:
                wx.CallAfter(wx.EndBusyCursor)
                def notifyUserOfDuplicateInstrumentName():
                    message = "Instrument name \"%s\" already exists in " \
                        "facility \"%s\"." \
                        % (event.newInstrumentName,
                           event.facilityName)
                    dlg = wx.MessageDialog(None, message, "MyData",
                                           wx.OK | wx.ICON_ERROR)
                    dlg.ShowModal()
                    event.settingsDialog.instrumentNameField.SetFocus()
                    event.settingsDialog.instrumentNameField.SelectAll()
                wx.CallAfter(notifyUserOfDuplicateInstrumentName)
            logger.debug("Finishing run() method for thread %s" % threading.current_thread().name)

        renameInstrumentThread = \
            threading.Thread(target=renameInstrumentWorker,
                             name="RenameInstrumentThread")
        myDataThreads.Add(renameInstrumentThread)
        logger.debug("Starting thread %s" % renameInstrumentThread.name)
        renameInstrumentThread.start()
        logger.debug("Started thread %s" % renameInstrumentThread.name)

    def SettingsDialogValidation(event):
        if event.id != EVT_SETTINGS_DIALOG_VALIDATION:
            event.Skip()
            return
        tempSettingsModel = SettingsModel()
        tempSettingsModel.SaveFieldsFromDialog(event.settingsDialog)

        def validate(tempSettingsModel):
            logger.debug("Starting run() method for thread %s" % threading.current_thread().name)
            try:
                wx.CallAfter(wx.BeginBusyCursor)
                tempSettingsModel.Validate()
                def endBusyCursorIfRequired():
                    try:
                        wx.EndBusyCursor()
                    except wx._core.PyAssertionError, e:
                        if not "no matching wxBeginBusyCursor()" in str(e):
                            logger.error(str(e))
                            raise
                wx.CallAfter(endBusyCursorIfRequired)
                if tempSettingsModel.IsIncompatibleMyTardisVersion():
                    return
                provideSettingsValidationResultsEvent = MyDataEvent(
                    EVT_PROVIDE_SETTINGS_VALIDATION_RESULTS,
                    settingsDialog=event.settingsDialog,
                    settingsModel=event.settingsModel,
                    tempSettingsModel=tempSettingsModel)
                wx.PostEvent(wx.GetApp().GetMainFrame(), provideSettingsValidationResultsEvent)
            except IncompatibleMyTardisVersion, e:
                logger.debug("Finished running tempSettingsModel.Validate() 3")
                def endBusyCursorIfRequired():
                    try:
                        wx.EndBusyCursor()
                    except wx._core.PyAssertionError, e:
                        if not "no matching wxBeginBusyCursor()" in str(e):
                            logger.error(str(e))
                            raise
                wx.CallAfter(endBusyCursorIfRequired)
                def showDialog():
                    message = str(e)
                    logger.error(message)
                    try:
                        wx.EndBusyCursor()
                    except wx._core.PyAssertionError, e:
                        if "no matching wxBeginBusyCursor()" \
                                not in str(e):
                            logger.error(str(e))
                            raise
                    dlg = wx.MessageDialog(None, message, "MyData",
                                           wx.OK | wx.ICON_ERROR)
                    dlg.ShowModal()
                wx.CallAfter(showDialog)
            logger.debug("Finished running tempSettingsModel.Validate() 4")
            logger.debug("Finishing run() method for thread %s" % threading.current_thread().name)

        thread = threading.Thread(target=validate,
                                  args=(tempSettingsModel,),
                                  name="TempSettingsModelValidationThread")
        logger.debug("Starting thread %s" % thread.name)
        thread.start()
        logger.debug("Started thread %s" % thread.name)

    def ProvideSettingsValidationResults(event):
        if event.id != EVT_PROVIDE_SETTINGS_VALIDATION_RESULTS:
            event.Skip()
            return
        tempSettingsModel = event.tempSettingsModel
        settingsValidation = tempSettingsModel.GetValidation()
        if settingsValidation is not None and \
                not settingsValidation.GetValid():
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
                        event.settingsDialog.SetInstrumentName(settingsValidation
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
            logger.debug("Settings were not valid, so Settings dialog "
                         "should remain visible.")
            return

        logger.debug("Settings were valid, so we'll save the settings "
                     "to disk and close the Settings dialog.")
        try:
            tempUploaderModel = tempSettingsModel.GetUploaderModel()
            tempUploaderModel.SetSettingsModel(event.settingsModel)
            event.settingsModel.SetUploaderModel(tempUploaderModel)
            tempInstrument = tempSettingsModel.GetInstrument()
            tempInstrument.SetSettingsModel(event.settingsModel)
            event.settingsModel.SaveFieldsFromDialog(event.settingsDialog)
            event.settingsModel.SetInstrument(tempSettingsModel.GetInstrument())
            event.settingsDialog.EndModal(wx.ID_OK)
            event.settingsDialog.Show(False)
            # event.settingsDialog.Destroy()
            logger.debug("Closed Settings dialog.")
        except:
            logger.debug(traceback.format_exc())

        def ProvideSettingsValidationResultsWorker3():
            logger.debug("Starting run() method for thread %s" % threading.current_thread().name)
            logger.debug("Finishing run() method for thread %s" % threading.current_thread().name)

        thread = threading.Thread(target=ProvideSettingsValidationResultsWorker3, name="ProvideSettingsValidationResultsWorkerThread-3")
        logger.debug("OnSettings: Starting ProvideSettingsValidationResultsWorker3 thread from %s." % threading.current_thread().name)
        thread.start()
        logger.debug("OnSettings: Started ProvideSettingsValidationResultsWorker3 thread.")


    def ShutdownForRefresh(event):
        if event.id != EVT_SHUTDOWN_FOR_REFRESH:
            event.Skip()
            return
        def shutdownForRefreshWorker():
            logger.debug("Starting run() method for thread %s" % threading.current_thread().name)
            logger.debug("Shutting down for refresh from %s."
                % threading.current_thread().name)
            try:
                wx.CallAfter(wx.BeginBusyCursor)
                event.foldersController.ShutDownUploadThreads()
                shutdownForRefreshCompleteEvent = MyDataEvent(
                    EVT_SHUTDOWN_FOR_REFRESH_COMPLETE,
                    shutdownSuccessful=True)
                wx.PostEvent(wx.GetApp().GetMainFrame(),
                             shutdownForRefreshCompleteEvent)
                wx.CallAfter(wx.EndBusyCursor)
            except:
                logger.debug(traceback.format_exc())
                message = "An error occurred while trying to shut down " \
                    "the existing data-scan-and-upload process in order " \
                    "to start another one.\n\n" \
                    "See the Log tab for details of the error."
                logger.error(message)

                def showDialog():
                    dlg = wx.MessageDialog(None, message, "MyData",
                                           wx.OK | wx.ICON_ERROR)
                    dlg.ShowModal()
                wx.CallAfter(showDialog)
            logger.debug("Finishing run() method for thread %s" % threading.current_thread().name)

        shutdownForRefreshThread = \
            threading.Thread(target=shutdownForRefreshWorker,
                             name="ShutdownForRefreshThread")
        myDataThreads.Add(shutdownForRefreshThread)
        logger.debug("Starting thread %s" % shutdownForRefreshThread.name)
        shutdownForRefreshThread.start()
        logger.debug("Started thread %s" % shutdownForRefreshThread.name)

    def ShutdownForRefreshComplete(event):
        if event.id != EVT_SHUTDOWN_FOR_REFRESH_COMPLETE:
            event.Skip()
            return
        wx.GetApp().OnRefresh(event)

    def SettingsValidationForRefresh(event):
        if event.id != EVT_SETTINGS_VALIDATION_FOR_REFRESH:
            event.Skip()
            return
        wx.GetApp().OnRefresh(event)

    def SettingsValidationForRefreshComplete(event):
        if event.id != EVT_SETTINGS_VALIDATION_FOR_REFRESH_COMPLETE:
            event.Skip()
            return
        wx.GetApp().OnRefresh(event)

    def StartDataUploads(event):
        if event.id != EVT_START_DATA_UPLOADS:
            event.Skip()
            return

        def startDataUploadsWorker():
            logger.debug("Starting run() method for thread %s" % threading.current_thread().name)
            logger.debug("startDataUploadsWorker")
            wx.CallAfter(wx.BeginBusyCursor)
            wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage,
                         "Starting data uploads...")
            event.foldersController.StartDataUploads()
            def endBusyCursorIfRequired():
                try:
                    wx.EndBusyCursor()
                except wx._core.PyAssertionError, e:
                    if not "no matching wxBeginBusyCursor()" in str(e):
                        logger.error(str(e))
                        raise
            wx.CallAfter(endBusyCursorIfRequired)
            logger.debug("Finishing run() method for thread %s" % threading.current_thread().name)

        startDataUploadsThread = \
            threading.Thread(target=startDataUploadsWorker,
                             name="StartDataUploadsThread")
        myDataThreads.Add(startDataUploadsThread)
        logger.debug("Starting thread %s" % startDataUploadsThread.name)
        startDataUploadsThread.start()
        logger.debug("Started thread %s" % startDataUploadsThread.name)


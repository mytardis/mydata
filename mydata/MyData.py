"""
MyData.py

Main module for MyData.

To run MyData from the command-line, use "python run.py", where run.py is
in the parent directory of the directory containing MyData.py.
"""
import sys
import os
import traceback
import threading
import argparse
import logging
import subprocess

import appdirs
import wx

from . import __version__ as VERSION
from . import LATEST_COMMIT
from .settings import SETTINGS
from .dataviewmodels.folders import FoldersModel
from .controllers.folders import FoldersController
from .views.mydata import MyDataFrame
from .dataviewmodels.users import UsersModel
from .dataviewmodels.groups import GroupsModel
from .dataviewmodels.verifications import VerificationsModel
from .dataviewmodels.uploads import UploadsModel
from .dataviewmodels.tasks import TasksModel
from .models.settings.serialize import LoadSettings
from .models.settings.validation import ValidateSettings
from .views.mydata import NotebookTabs
from .views.settings import SettingsDialog
from .utils.exceptions import InvalidFolderStructure
from .utils.exceptions import InvalidSettings
from .utils.exceptions import UserAbortedSettingsValidation
from .logs import logger
from .events import MYDATA_EVENTS
from .events import PostEvent
from .utils.notification import Notification
from .models.settings import LastSettingsUpdateTrigger
from .controllers.schedule import ScheduleController
from .views.testrun import TestRunFrame
from .utils import BeginBusyCursorIfRequired
from .utils import EndBusyCursorIfRequired
from .utils import HandleGenericErrorWithDialog
from .utils.connectivity import Connectivity
from .threads.flags import FLAGS
from .threads.locks import LOCKS
from .views.connectivity import ReportNoActiveInterfaces
if sys.platform.startswith("linux"):
    from .linuxsubprocesses import StopErrandBoy


class MyData(wx.App):
    """
    Encapsulates the MyData application.
    """
    # piylint: disable=too-many-public-methods

    def __init__(self, argv):
        self.instance = None

        self.frame = None

        # The Test Run frame summarizes the results of a dry run:
        self.testRunFrame = None

        self.connectivity = Connectivity()

        self.dataViewModels = dict()

        self.foldersController = None
        self.scheduleController = None

        MyData.ParseArgs(argv)

        wx.App.__init__(self, redirect=False)

    @staticmethod
    def ParseArgs(argv):
        """
        Parse command-line arguments.
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("-v", "--version", action="store_true",
                            help="Display MyData version and exit")
        parser.add_argument("-l", "--loglevel", help="set logging verbosity")
        args, _ = parser.parse_known_args(argv[1:])
        if args.version:
            sys.stdout.write("MyData %s (%s)\n" % (VERSION, LATEST_COMMIT))
            sys.exit(0)
        if args.loglevel:
            if args.loglevel.upper() == "DEBUG":
                logger.SetLevel(logging.DEBUG)
            elif args.loglevel.upper() == "INFO":
                logger.SetLevel(logging.INFO)
            elif args.loglevel.upper() == "WARN":
                logger.SetLevel(logging.WARN)
            elif args.loglevel.upper() == "ERROR":
                logger.SetLevel(logging.ERROR)

    def OnInit(self):
        """
        Called automatically when application instance is created.
        """
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        self.SetAppName("MyData")
        appname = "MyData"
        if sys.platform.startswith("win"):
            # We use a setup wizard on Windows which runs with admin
            # privileges, so we can ensure that the appdirPath below,
            # i.e. C:\ProgramData\Monash University\MyData\ is
            # writeable by all users.
            appdirPath = appdirs.site_config_dir(appname, "Monash University")
        else:
            # On Mac, we currently use a DMG drag-and-drop installation, so
            # we can't create a system-wide MyData.cfg writeable by all users.
            appdirPath = appdirs.user_data_dir(appname, "Monash University")
        if not os.path.exists(appdirPath):
            os.makedirs(appdirPath)

        if hasattr(sys, "frozen"):
            if sys.platform.startswith("darwin"):
                certPath = os.path.realpath('.')
            else:
                certPath = os.path.dirname(sys.executable)
            os.environ['REQUESTS_CA_BUNDLE'] = \
                os.path.join(certPath, 'cacert.pem')

        if not SETTINGS.configPath:
            # SETTINGS.configPath is set to None in mydata/settings.py
            # but it could be overwritten in unittests.
            SETTINGS.configPath = os.path.join(appdirPath, appname + '.cfg')
            # Load settings from MyData.cfg, stored in INI format:
            LoadSettings(SETTINGS)

        self.dataViewModels = dict(
            users=UsersModel(),
            groups=GroupsModel(),
            verifications=VerificationsModel(),
            uploads=UploadsModel(),
            tasks=TasksModel())
        self.dataViewModels['folders'] = \
            FoldersModel(self.dataViewModels['users'],
                         self.dataViewModels['groups'])

        self.frame = MyDataFrame("MyData", self.dataViewModels)

        # Wait until views have been created (in MyDataFrame) before doing
        # logging, so that the logged messages will appear in the Log View:
        logger.info("MyData version: v%s" % VERSION)
        logger.info("MyData commit:  %s" % LATEST_COMMIT)
        logger.info("appdirPath: " + appdirPath)
        logger.info("SETTINGS.configPath: " + SETTINGS.configPath)

        self.frame.Bind(wx.EVT_ACTIVATE_APP, self.OnActivateApp)
        MYDATA_EVENTS.InitializeWithNotifyWindow(self.frame)
        self.testRunFrame = TestRunFrame(self.frame)

        self.foldersController = FoldersController(self.frame, self.dataViewModels)
        self.scheduleController = ScheduleController(self.dataViewModels['tasks'])

        if sys.platform.startswith("win"):
            self.CheckIfAlreadyRunning(appdirPath)

        self.frame.Bind(wx.EVT_CLOSE, self.OnCloseFrame)
        self.frame.Bind(wx.EVT_ICONIZE, self.OnMinimizeFrame)
        self.SetTopWindow(self.frame)

        event = None
        if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ and \
                SETTINGS.RequiredFieldIsBlank():
            self.frame.Show(True)
            self.OnSettings(event)
        else:
            self.frame.SetTitle("MyData - " + SETTINGS.general.instrumentName)
            if sys.platform.startswith("linux"):
                if os.getenv('DESKTOP_SESSION', '') == 'ubuntu':
                    proc = subprocess.Popen(['dpkg', '-s',
                                             'indicator-systemtray-unity'],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
                    _ = proc.communicate()
                    if proc.returncode != 0:
                        message = "Running MyData on Ubuntu's default " \
                            "(Unity) desktop requires the " \
                            "indicator-systemtray-unity package: " \
                            "https://github.com/GGleb/" \
                            "indicator-systemtray-unity"
                        wx.MessageBox(message, "MyData", wx.ICON_ERROR)
                        sys.exit(1)
            self.frame.Hide()
            title = "MyData"
            if sys.platform.startswith("darwin"):
                message = \
                    "Click the MyData menubar icon to access its menu."
            else:
                message = \
                    "Click the MyData system tray icon to access its menu."
            Notification.Notify(message, title=title)
            if 'MYDATA_TESTING' in os.environ:
                if 'MYDATA_DONT_RUN_SCHEDULE' not in os.environ:
                    self.scheduleController.ApplySchedule(event)
            else:
                # wx.CallAfter is used to wait until the main loop has started
                # and then become idle before applying the schedule, otherwise
                # the GUI can appear frozen while the "On Startup" task is
                # beginning.
                wx.CallAfter(self.scheduleController.ApplySchedule, event)

        return True

    def CheckIfAlreadyRunning(self, appdirPath):
        """
        Using wx.SingleInstanceChecker to check whether MyData is already
        running.  Only used on Windows at present.
        """
        self.instance = wx.SingleInstanceChecker("MyData", path=appdirPath)
        if self.instance.IsAnotherRunning():
            message = "MyData is already running!"
            if wx.PyApp.IsMainLoopRunning():
                wx.MessageBox("MyData is already running!", "MyData",
                              wx.ICON_ERROR)
                sys.exit(1)
            else:
                sys.stderr.write("%s\n" % message)

    def OnActivateApp(self, event):
        """
        Called when MyData is activated.
        """
        if event.GetActive():
            if sys.platform.startswith("darwin"):
                self.frame.Show(True)
                self.frame.Raise()
        event.Skip()

    def OnCloseFrame(self, event):
        """
        Don't actually close it, just hide it.
        """
        event.StopPropagation()
        if sys.platform.startswith("win"):
            self.frame.Show()  # See: http://trac.wxwidgets.org/ticket/10426
        self.frame.Hide()

    def ShutDownCleanlyAndExit(self, event, confirm=True):
        """
        Shut down MyData cleanly and quit.
        """
        event.StopPropagation()
        okToExit = wx.ID_YES
        if confirm and self.Processing():
            message = "Are you sure you want to shut down MyData's " \
                "data scans and uploads?"
            if self.Processing():
                message += "\n\n" \
                    "MyData will attempt to shut down any uploads currently " \
                    "in progress."
            confirmationDialog = \
                wx.MessageDialog(None, message, "MyData",
                                 wx.YES | wx.NO | wx.ICON_QUESTION)
            okToExit = confirmationDialog.ShowModal()
        if okToExit == wx.ID_YES:
            BeginBusyCursorIfRequired()
            self.foldersController.ShutDownUploadThreads()
            EndBusyCursorIfRequired()
            self.dataViewModels['tasks'].ShutDown()
            if sys.platform.startswith("linux"):
                StopErrandBoy()
            # sys.exit can raise exceptions if the wx.App
            # is shutting down:
            os._exit(0)  # pylint: disable=protected-access

    def OnMinimizeFrame(self, event):
        """
        When minimizing, hide the frame so it "minimizes to tray"
        """
        if event.Iconized():
            self.frame.Show()  # See: http://trac.wxwidgets.org/ticket/10426
            self.frame.Hide()
        else:
            self.frame.Show(True)
            self.frame.Raise()
        # event.Skip()

    def OnScanAndUploadFromToolbar(self, event):
        """
        The user pressed the Upload icon on the main window's toolbar.
        """
        logger.debug("OnScanAndUploadFromToolbar")
        self.ScanFoldersAndUpload(event)

    def ScanFoldersAndUpload(self, event):
        """
        Scan folders and upload datafiles if necessary.
        """
        SETTINGS.schedule.scheduleType = "Manually"
        SETTINGS.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.UI_RESPONSE
        self.ResetShouldAbortStatus()
        self.scheduleController.ApplySchedule(event, runManually=True)

    def OnTestRunFromToolbar(self, event):
        """
        The user pressed the Test Run icon on the main window's toolbar.
        """
        logger.debug("OnTestRunFromToolbar")
        FLAGS.testRunRunning = True
        SETTINGS.schedule.scheduleType = "Manually"
        SETTINGS.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.UI_RESPONSE
        self.frame.toolbar.DisableTestAndUploadToolbarButtons()
        self.testRunFrame.saveButton.Disable()
        self.ResetShouldAbortStatus()
        self.scheduleController.ApplySchedule(event, runManually=True,
                                              needToValidateSettings=True,
                                              testRun=True)
        self.testRunFrame.Show()
        self.testRunFrame.Clear()
        self.testRunFrame.SetTitle("%s - Test Run" % self.frame.GetTitle())
        logger.testrun("Starting Test Run...")

    def CheckIfShouldAbort(self):
        """
        Check if user has requested aborting scans and uploads,
        and if so, restores icons and cursors to their default state,
        and then raises an exception.
        """
        if FLAGS.shouldAbort or self.foldersController.canceled:
            self.RestoreUserInterfaceForAbort()
            return True
        return False

    def RestoreUserInterfaceForAbort(self):
        """
        Restores icons and cursors to their default state.
        """
        wx.CallAfter(EndBusyCursorIfRequired)
        wx.CallAfter(self.frame.toolbar.EnableTestAndUploadToolbarButtons)
        if self.testRunFrame.IsShown():
            wx.CallAfter(self.testRunFrame.Hide)
        FLAGS.scanningFolders = False
        FLAGS.testRunRunning = False

    def ResetShouldAbortStatus(self):
        """
        Resets the ShouldAbort status
        """
        FLAGS.shouldAbort = False
        self.foldersController.ClearStatusFlags()

    def OnRefresh(self, event, needToValidateSettings=True, jobId=None,
                  testRun=False):
        """
        Shut down any existing data folder scan and upload threads,
        validate settings, and begin scanning data folders, checking
        for existing datafiles on MyTardis and uploading any datafiles
        not yet available on MyTardis.
        """
        self.LogOnRefreshCaller(event, jobId)
        if self.CheckIfShouldAbort():
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
            self.frame.SetStatusMessage(message)

            shutdownForRefreshEvent = \
                MYDATA_EVENTS.ShutdownForRefreshEvent(
                    foldersController=self.foldersController,
                    testRun=testRun)
            logger.debug("Posting shutdownForRefreshEvent")
            PostEvent(shutdownForRefreshEvent)
            return

        self.foldersController.SetShuttingDown(False)

        self.frame.toolbar.searchCtrl.SetValue("")

        # Settings validation:

        if needToValidateSettings:
            validateSettingsForRefreshEvent = \
                MYDATA_EVENTS.ValidateSettingsForRefreshEvent(
                    needToValidateSettings=needToValidateSettings,
                    testRun=testRun)
            if self.connectivity.CheckForRefresh(
                    nextEvent=validateSettingsForRefreshEvent):
                # Wait for the event to be handled, which will result
                # in OnRefresh being called again.
                return

            logger.debug("OnRefresh: needToValidateSettings is True.")
            message = "Validating settings..."
            self.frame.SetStatusMessage(message)
            logger.info(message)
            if testRun:
                logger.testrun(message)

            def ValidateSettingsWorker():
                """
                Validate settings.
                """
                logger.debug("Starting run() method for thread %s"
                             % threading.current_thread().name)
                activeNetworkInterfaces = []
                try:
                    wx.CallAfter(BeginBusyCursorIfRequired)
                    try:
                        activeNetworkInterfaces = \
                            Connectivity.GetActiveNetworkInterfaces()
                    except Exception as err:
                        HandleGenericErrorWithDialog(err)
                    if len(activeNetworkInterfaces) == 0:
                        ReportNoActiveInterfaces()
                        return

                    try:
                        ValidateSettings(testRun=testRun)
                        event = MYDATA_EVENTS.SettingsValidationCompleteEvent(
                            testRun=testRun)
                        PostEvent(event)
                        wx.CallAfter(EndBusyCursorIfRequired)
                    except UserAbortedSettingsValidation:
                        self.RestoreUserInterfaceForAbort()
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
                            self.RestoreUserInterfaceForAbort()
                            self.frame.SetStatusMessage(
                                "Settings validation failed.")
                            if testRun:
                                wx.CallAfter(self.testRunFrame.Hide)
                            wx.CallAfter(self.OnSettings, None,
                                         validationMessage=message)
                            return
                except:
                    logger.error(traceback.format_exc())
                    return
                logger.debug("Finishing run() method for thread %s"
                             % threading.current_thread().name)

            if wx.PyApp.IsMainLoopRunning():
                thread = threading.Thread(target=ValidateSettingsWorker,
                                          name="OnRefreshValidateSettingsThread")
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
            self.frame.SetStatusMessage(message)
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
            if self.CheckIfShouldAbort():
                return
            self.foldersController.InitForUploads()
            if self.CheckIfShouldAbort():
                return
            message = "Scanning data folders..."
            wx.CallAfter(self.frame.SetStatusMessage, message)
            message = "Scanning data folders in %s..." \
                % SETTINGS.general.dataDirectory
            logger.info(message)
            if testRun:
                logger.testrun(message)
            try:
                LOCKS.scanningFoldersThreadingLock.acquire()
                FLAGS.scanningFolders = True
                logger.debug("Just set scanningFolders to True")
                wx.CallAfter(self.frame.toolbar.DisableTestAndUploadToolbarButtons)
                self.dataViewModels['folders'].ScanFolders(
                    WriteProgressUpdateToStatusBar)
                self.foldersController.FinishedScanningForDatasetFolders()
                FLAGS.scanningFolders = False
                LOCKS.scanningFoldersThreadingLock.release()
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
                self.frame.SetStatusMessage(str(ifs))
                return

            if self.CheckIfShouldAbort():
                self.RestoreUserInterfaceForAbort()
                if testRun:
                    logger.testrun("Data scans and uploads were canceled.")
                    FLAGS.testRunRunning = False
                return

            folderStructure = SETTINGS.advanced.folderStructure
            usersModel = self.dataViewModels['users']
            groupsModel = self.dataViewModels['groups']
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
                wx.CallAfter(self.frame.SetStatusMessage, message)
                self.RestoreUserInterfaceForAbort()
            wx.CallAfter(EndBusyCursorIfRequired)

        if wx.PyApp.IsMainLoopRunning():
            thread = threading.Thread(target=ScanDataDirs,
                                      name="ScanDataDirectoriesThread")
            thread.start()
        else:
            ScanDataDirs()

    def LogOnRefreshCaller(self, event, jobId):
        """
        Called by OnRefresh (the main method for starting the
        data folder scans and uploads) to log what triggered the
        call to OnRefresh (e.g. the toolbar button, the task bar
        icon menu item, or a scheduled task).
        """
        try:
            syncNowMenuItemId = \
                self.frame.taskBarIcon.GetSyncNowMenuItem().GetId()
        except (AttributeError, RuntimeError):
            syncNowMenuItemId = None
        if jobId:
            logger.debug("OnRefresh called from job ID %d" % jobId)
        elif event is None:
            logger.debug("OnRefresh called automatically "
                         "from MyData's OnInit().")
        elif event.GetId() == self.frame.toolbar.settingsTool.GetId():
            logger.debug("OnRefresh called automatically from "
                         "OnSettings(), after displaying SettingsDialog, "
                         "which was launched from MyData's toolbar.")
        elif event.GetId() == self.frame.toolbar.uploadTool.GetId():
            logger.debug("OnRefresh triggered by Upload toolbar icon.")
        elif syncNowMenuItemId and event.GetId() == syncNowMenuItemId:
            logger.debug("OnRefresh triggered by 'Sync Now' "
                         "task bar menu item.")
        elif event.GetEventType() == \
                MYDATA_EVENTS.EVT_VALIDATE_SETTINGS_FOR_REFRESH:
            logger.debug("OnRefresh called from "
                         "EVT_VALIDATE_SETTINGS_FOR_REFRESH event.")
        elif event.GetEventType() == \
                MYDATA_EVENTS.EVT_SETTINGS_VALIDATION_COMPLETE:
            logger.debug("OnRefresh called from "
                         "EVT_SETTINGS_VALIDATION_COMPLETE event.")
        elif event.GetEventType() == \
                MYDATA_EVENTS.EVT_SHUTDOWN_FOR_REFRESH_COMPLETE:
            logger.debug("OnRefresh called from "
                         "EVT_SHUTDOWN_FOR_REFRESH_COMPLETE event.")
        elif event.GetEventType() == \
                MYDATA_EVENTS.EVT_SETTINGS_VALIDATION_COMPLETE:
            logger.debug("OnRefresh called from "
                         "EVT_SETTINGS_VALIDATION_COMPLETE event.")
        else:
            logger.debug("OnRefresh: event.GetEventType() = %s"
                         % event.GetEventType())

    def OnStop(self, event):
        """
        The user pressed the stop button on the main toolbar.
        """
        FLAGS.shouldAbort = True
        if self.foldersController.started:
            BeginBusyCursorIfRequired()
            PostEvent(
                self.foldersController.ShutdownUploadsEvent(canceled=True))
        else:
            self.RestoreUserInterfaceForAbort()
            message = "Data scans and uploads were canceled."
            logger.info(message)
            self.frame.SetStatusMessage(message)
        if event:
            event.Skip()

    def OnOpen(self, event):
        """
        Open the selected data folder in Windows Explorer (Windows) or
        in Finder (Mac OS X).
        """
        if self.frame.tabbedView.GetSelection() == NotebookTabs.FOLDERS:
            self.foldersController.OnOpenFolder(event)

    def OnSettings(self, event, validationMessage=None):
        """
        Open the Settings dialog, which could be in response to the main
        toolbar's Refresh icon, or in response to in response to the task bar
        icon's "MyData Settings" menu item, or in response to MyData being
        launched without any previously saved settings.
        """
        # When Settings is launched by user e.g. from the toolbar, we don't
        # want it to be aborted, so we'll ensure FLAGS.shouldAbort is False.
        if event:
            self.ResetShouldAbortStatus()
        self.frame.SetStatusMessage("")
        settingsDialog = SettingsDialog(self.frame,
                                        size=wx.Size(400, 400),
                                        style=wx.DEFAULT_DIALOG_STYLE,
                                        validationMessage=validationMessage)
        if settingsDialog.ShowModal() == wx.ID_OK:
            logger.debug("settingsDialog.ShowModal() returned wx.ID_OK")
            self.frame.SetTitle("MyData - " + SETTINGS.general.instrumentName)
            self.dataViewModels['tasks'].DeleteAllRows()
            self.scheduleController.ApplySchedule(event)

    def Processing(self):
        """
        Returns True/False, depending on whether MyData is
        currently busy processing something.
        """
        try:
            return self.frame.toolbar.GetToolEnabled(self.frame.toolbar.stopTool.GetId())
        except wx.PyDeadObjectError:  # Exception no longer exists in Phoenix.
            return False


def Run(argv):
    """
    Main function for launching MyData.
    """
    app = MyData(argv)
    app.MainLoop()


if __name__ == "__main__":
    sys.stderr.write(
        "Please use run.py in MyData.py's parent directory instead.\n")

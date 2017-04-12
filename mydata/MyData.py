"""
MyData.py

Main module for MyData.

To run MyData from the command-line, use "python run.py", where run.py is
in the parent directory of the directory containing MyData.py.
"""

# pylint: disable=too-many-lines
# pylint: disable=wrong-import-position

import sys
import os
import traceback
import threading
import argparse
import logging
import subprocess
import webbrowser

import appdirs
import requests

import wx
if wx.version().startswith("3.0.3.dev"):
    from wx import Icon as EmptyIcon
    from wx.adv import EVT_TASKBAR_LEFT_UP
    from wx.adv import EVT_TASKBAR_LEFT_DOWN
    from wx.lib.agw.aui import AuiNotebook
    from wx.lib.agw.aui import AUI_NB_TOP
    from wx.lib.agw.aui import EVT_AUINOTEBOOK_PAGE_CHANGING
else:
    from wx import EmptyIcon
    from wx import EVT_TASKBAR_LEFT_UP
    from wx import EVT_TASKBAR_LEFT_DOWN
    from wx.aui import AuiNotebook
    from wx.aui import AUI_NB_TOP
    from wx.aui import EVT_AUINOTEBOOK_PAGE_CHANGING

from . import __version__ as VERSION
from . import LATEST_COMMIT
from .settings import SETTINGS
from .dataviewmodels.folders import FoldersModel
from .controllers.folders import FoldersController
from .views.dataview import MyDataDataView
from .dataviewmodels.users import UsersModel
from .dataviewmodels.groups import GroupsModel
from .dataviewmodels.verifications import VerificationsModel
from .dataviewmodels.uploads import UploadsModel
from .dataviewmodels.tasks import TasksModel
from .views.log import LogView
from .models.settings.serialize import LoadSettings
from .models.settings.validation import ValidateSettings
from .views.settings import SettingsDialog
from .utils.exceptions import InvalidFolderStructure
from .utils.exceptions import InvalidSettings
from .logs import logger
from .views.taskbaricon import MyDataTaskBarIcon
from .events import MYDATA_EVENTS
from .events import PostEvent
from .media import MYDATA_ICONS
from .media import IconStyle
from .utils.notification import Notification
from .models.settings import LastSettingsUpdateTrigger
from .controllers.schedule import ScheduleController
from .views.testrun import TestRunFrame
from .utils import BeginBusyCursorIfRequired
from .utils import EndBusyCursorIfRequired
from .utils import HandleGenericErrorWithDialog
from .utils.connectivity import Connectivity
from .views.connectivity import ReportNoActiveInterfaces
if sys.platform.startswith("linux"):
    from .linuxsubprocesses import StopErrandBoy


class NotebookTabs(object):
    """
    Enumerated data type for referencing the different tab views in
    MyData's main window.
    """
    FOLDERS = 0
    USERS = 1
    GROUPS = 2
    VERIFICATIONS = 3
    UPLOADS = 4
    LOG = 5


class MyDataFrame(wx.Frame):
    """
    MyData's main window.
    """
    def __init__(self, title, style):
        wx.Frame.__init__(self, None, wx.ID_ANY, title, style=style)
        self.SetSize(wx.Size(1000, 600))
        self.statusbar = wx.StatusBar(self)
        if sys.platform.startswith("win"):
            self.statusbar.SetSize(wx.Size(-1, 28))
        else:
            self.statusbar.SetSize(wx.Size(-1, 18))
        self.statusbar.SetFieldsCount(2)
        self.SetStatusBar(self.statusbar)
        self.statusbar.SetStatusWidths([-1, 60])
        self.connectedBitmap = MYDATA_ICONS.GetIcon("Connect")
        self.disconnectedBitmap = MYDATA_ICONS.GetIcon("Disconnect")
        self.connected = False

    def SetStatusMessage(self, msg):
        """
        Update status bar's message.
        """
        if sys.platform.startswith("win"):
            # On Windows, a tab can be used to center status text,
            # which look similar to the old EnhancedStatusBar.
            self.statusbar.SetStatusText("\t%s" % msg)
        else:
            self.statusbar.SetStatusText(msg)
        if sys.platform.startswith("win"):
            if wx.PyApp.IsMainLoopRunning():
                wx.GetApp().taskBarIcon.SetIcon(wx.GetApp().taskBarIcon.icon, msg)


class MyData(wx.App):
    """
    Encapsulates the MyData application.
    """
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods

    def __init__(self, argv, okToShowModalDialogs=True, okToRunSchedule=True):
        self.name = "MyData"
        self.argv = argv
        self.okToShowModalDialogs = okToShowModalDialogs
        self.okToRunSchedule = okToRunSchedule

        self.instance = None

        self.configPath = None

        self.frame = None
        self.testRunFrame = None
        self.panel = None
        self.tabbedView = None

        self.menuBar = None
        self.editMenu = None
        self.helpMenu = None

        self.toolbar = None
        self.settingsTool = None
        self.stopTool = None
        self.testTool = None
        self.uploadTool = None
        self.myTardisTool = None
        self.aboutTool = None
        self.helpTool = None

        self.taskBarIcon = None

        self.searchCtrl = None

        self.scanningFolders = threading.Event()
        self.performingLookupsAndUploads = threading.Event()
        self.testRunRunning = threading.Event()
        self.shouldAbort = threading.Event()

        self.scanningFoldersThreadingLock = threading.Lock()

        self.connectivity = Connectivity()

        self.foldersModel = None
        self.foldersView = None
        self.foldersController = None
        self.scheduleController = None
        self.usersModel = None
        self.usersView = None
        self.groupsModel = None
        self.groupsView = None
        self.verificationsModel = None
        self.verificationsView = None
        self.uploadsModel = None
        self.uploadsView = None
        self.tasksModel = None
        self.tasksView = None
        self.logView = None

        wx.App.__init__(self, redirect=False)

    # This method is too long.  Needs refactoring.
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def OnInit(self):
        """
        Called automatically when application instance is created.
        """
        self.SetAppName("MyData")  # pylint: disable=no-member
        logger.debug("self.argv = " + str(self.argv))
        logger.debug("MyData version:   " + VERSION)
        logger.debug("MyData commit:  " + LATEST_COMMIT)
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
        logger.debug("appdirPath: " + appdirPath)
        if not os.path.exists(appdirPath):
            os.makedirs(appdirPath)

        if hasattr(sys, "frozen"):
            if sys.platform.startswith("darwin"):
                certPath = os.path.realpath('.')
            else:
                certPath = os.path.dirname(sys.executable)
            os.environ['REQUESTS_CA_BUNDLE'] = \
                os.path.join(certPath, 'cacert.pem')

        parser = argparse.ArgumentParser()
        parser.add_argument("-v", "--version", action="store_true",
                            help="Display MyData version and exit")
        parser.add_argument("-l", "--loglevel", help="set logging verbosity")
        args, _ = parser.parse_known_args(self.argv[1:])
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

        # MyData.cfg stores settings in INI format, readable by ConfigParser
        self.SetConfigPath(os.path.join(appdirPath, appname + '.cfg'))
        logger.debug("self.GetConfigPath(): " + self.GetConfigPath())
        if not SETTINGS.configPath:
            SETTINGS.configPath = self.GetConfigPath()
            LoadSettings(SETTINGS, self.GetConfigPath())
        self.frame = MyDataFrame(self.name, style=wx.DEFAULT_FRAME_STYLE)

        self.frame.Bind(wx.EVT_ACTIVATE_APP, self.OnActivateApp)
        MYDATA_EVENTS.InitializeWithNotifyWindow(self.frame)
        self.testRunFrame = TestRunFrame(self.frame)

        if sys.platform.startswith("win"):
            self.CheckIfAlreadyRunning(appdirPath)

        if sys.platform.startswith("darwin"):
            self.CreateMacMenu()

        self.usersModel = UsersModel()
        self.groupsModel = GroupsModel()
        self.foldersModel = FoldersModel(self.usersModel, self.groupsModel)
        self.usersModel.foldersModel = self.foldersModel
        self.verificationsModel = VerificationsModel()
        self.uploadsModel = UploadsModel()
        self.tasksModel = TasksModel()

        self.taskBarIcon = MyDataTaskBarIcon(self.frame)
        if sys.platform.startswith("linux"):
            self.taskBarIcon.Bind(EVT_TASKBAR_LEFT_DOWN, self.OnTaskBarLeftClick)
        else:
            self.taskBarIcon.Bind(EVT_TASKBAR_LEFT_UP, self.OnTaskBarLeftClick)

        self.frame.Bind(wx.EVT_MENU, self.taskBarIcon.OnExit, id=wx.ID_EXIT)

        self.frame.Bind(wx.EVT_CLOSE, self.OnCloseFrame)
        self.frame.Bind(wx.EVT_ICONIZE, self.OnMinimizeFrame)

        bmp = MYDATA_ICONS.GetIcon("favicon", vendor="MyTardis")
        icon = EmptyIcon()
        icon.CopyFromBitmap(bmp)
        self.frame.SetIcon(icon)

        self.panel = wx.Panel(self.frame)

        if wx.version().startswith("3.0.3.dev"):
            self.tabbedView = AuiNotebook(self.panel, agwStyle=AUI_NB_TOP)
        else:
            self.tabbedView = AuiNotebook(self.panel, style=AUI_NB_TOP)
        # Without the following line, the tab font looks
        # too small on Mac OS X:
        self.tabbedView.SetFont(self.panel.GetFont())
        self.frame.Bind(EVT_AUINOTEBOOK_PAGE_CHANGING,
                        self.OnNotebookPageChanging, self.tabbedView)

        self.foldersView = MyDataDataView(self.tabbedView, self.foldersModel)

        self.tabbedView.AddPage(self.foldersView, "Folders")
        self.foldersController = FoldersController(
            self.frame, self.foldersModel, self.foldersView, self.usersModel,
            self.verificationsModel, self.uploadsModel)

        self.scheduleController = ScheduleController(self.tasksModel)

        self.usersView = MyDataDataView(self.tabbedView, self.usersModel)
        self.tabbedView.AddPage(self.usersView, "Users")

        self.groupsView = MyDataDataView(self.tabbedView, self.groupsModel)
        self.tabbedView.AddPage(self.groupsView, "Groups")

        self.verificationsView = MyDataDataView(
            self.tabbedView, self.verificationsModel)
        self.tabbedView.AddPage(self.verificationsView, "Verifications")

        self.uploadsView = MyDataDataView(self.tabbedView, self.uploadsModel)
        self.tabbedView.AddPage(self.uploadsView, "Uploads")

        self.tasksView = MyDataDataView(self.tabbedView, self.tasksModel)
        self.tabbedView.AddPage(self.tasksView, "Tasks")

        self.logView = LogView(self.tabbedView)
        self.tabbedView.AddPage(self.logView, "Log")

        self.CreateToolbar()

        sizer = wx.BoxSizer()
        sizer.Add(self.tabbedView, 1, flag=wx.EXPAND)
        self.panel.SetSizer(sizer)

        sizer = wx.BoxSizer()
        sizer.Add(self.panel, 1, flag=wx.EXPAND)
        self.frame.SetSizer(sizer)

        self.tabbedView.SendSizeEvent()

        self.panel.SetFocus()

        self.SetTopWindow(self.frame)

        event = None
        if self.okToShowModalDialogs and SETTINGS.RequiredFieldIsBlank():
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
                if self.okToRunSchedule:
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
        self.instance = wx.SingleInstanceChecker(self.name, path=appdirPath)
        if self.instance.IsAnotherRunning():
            message = "MyData is already running!"
            if wx.PyApp.IsMainLoopRunning():
                wx.MessageBox("MyData is already running!", "MyData",
                              wx.ICON_ERROR)
                sys.exit(1)
            else:
                sys.stderr.write("%s\n" % message)

    def CreateMacMenu(self):
        """
        On Mac OS X, adding an Edit menu seems to help with
        enabling command-c (copy) and command-v (paste)
        """
        self.menuBar = wx.MenuBar()
        self.editMenu = wx.Menu()
        self.editMenu.Append(wx.ID_UNDO, "Undo\tCTRL+Z", "Undo")
        self.editMenu.Append(wx.ID_REDO, "Redo\tCTRL+SHIFT+Z", "Redo")
        self.editMenu.AppendSeparator()
        self.editMenu.Append(wx.ID_CUT, "Cut\tCTRL+X",
                             "Cut the selected text")
        self.editMenu.Append(wx.ID_COPY, "Copy\tCTRL+C",
                             "Copy the selected text")
        self.editMenu.Append(wx.ID_PASTE, "Paste\tCTRL+V",
                             "Paste text from the clipboard")
        self.editMenu.Append(wx.ID_SELECTALL, "Select All\tCTRL+A",
                             "Select All")
        self.menuBar.Append(self.editMenu, "Edit")

        self.helpMenu = wx.Menu()

        helpMenuItemID = wx.NewId()
        self.helpMenu.Append(helpMenuItemID, "&MyData Help")
        self.frame.Bind(wx.EVT_MENU, MyData.OnHelp, id=helpMenuItemID)

        walkthroughMenuItemID = wx.NewId()
        self.helpMenu.Append(
            walkthroughMenuItemID, "Mac OS X &Walkthrough")
        self.frame.Bind(wx.EVT_MENU, MyData.OnWalkthrough,
                        id=walkthroughMenuItemID)

        self.helpMenu.Append(wx.ID_ABOUT, "&About MyData")
        self.frame.Bind(wx.EVT_MENU, MyData.OnAbout, id=wx.ID_ABOUT)
        self.menuBar.Append(self.helpMenu, "&Help")
        self.frame.SetMenuBar(self.menuBar)

    def OnActivateApp(self, event):
        """
        Called when MyData is activated.
        """
        if event.GetActive():
            if sys.platform.startswith("darwin"):
                self.frame.Show(True)
                self.frame.Raise()
        event.Skip()

    def OnTaskBarLeftClick(self, event):
        """
        Called when task bar icon is clicked with the left mouse button.
        """
        self.taskBarIcon.PopupMenu(self.taskBarIcon.CreatePopupMenu())
        event.Skip()

    # pylint: disable=unused-argument
    def OnCloseFrame(self, event):
        """
        Don't actually close it, just hide it.
        """
        if sys.platform.startswith("win"):
            self.frame.Show()  # See: http://trac.wxwidgets.org/ticket/10426
        self.frame.Hide()

    # pylint: disable=unused-argument
    def ShutDownCleanlyAndExit(self, event, confirm=True):
        """
        Shut down MyData cleanly and quit.
        """
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
            self.tasksModel.ShutDown()
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

    def CreateToolbar(self):
        """
        Create a toolbar.
        """
        self.toolbar = self.frame.CreateToolBar()
        self.toolbar.SetToolBitmapSize(wx.Size(24, 24))  # sets icon size

        openIcon = MYDATA_ICONS.GetIcon("Open folder", size="24x24")
        if wx.version().startswith("3.0.3.dev"):
            addToolMethod = self.toolbar.AddTool
        else:
            addToolMethod = self.toolbar.AddLabelTool
        openTool = addToolMethod(wx.ID_ANY, "Open folder",
                                 openIcon, shortHelp="Open folder")
        self.frame.Bind(wx.EVT_MENU, self.OnOpen, openTool)

        self.toolbar.AddSeparator()

        testIcon = MYDATA_ICONS.GetIcon("Test tubes", size="24x24")
        self.testTool = addToolMethod(wx.ID_ANY, "Test Run",
                                      testIcon, shortHelp="Test Run")
        self.frame.Bind(wx.EVT_TOOL, self.OnTestRunFromToolbar, self.testTool,
                        self.testTool.GetId())

        self.toolbar.AddSeparator()

        uploadIcon = MYDATA_ICONS.GetIcon("Upload button", size="24x24")
        self.uploadTool = addToolMethod(wx.ID_ANY, "Scan and Upload",
                                        uploadIcon, shortHelp="Scan and Upload")
        self.frame.Bind(wx.EVT_TOOL, self.OnScanAndUploadFromToolbar, self.uploadTool,
                        self.uploadTool.GetId())

        self.toolbar.AddSeparator()

        stopIcon = MYDATA_ICONS.GetIcon("Stop sign", size="24x24",
                                        style=IconStyle.NORMAL)
        self.stopTool = addToolMethod(wx.ID_STOP, "Stop",
                                      stopIcon, shortHelp="Stop")
        disabledStopIcon = MYDATA_ICONS.GetIcon("Stop sign", size="24x24",
                                                style=IconStyle.DISABLED)
        self.toolbar.SetToolDisabledBitmap(self.stopTool.GetId(),
                                           disabledStopIcon)
        self.toolbar.EnableTool(self.stopTool.GetId(), False)

        self.frame.Bind(wx.EVT_TOOL, self.OnStop, self.stopTool,
                        self.stopTool.GetId())

        self.toolbar.AddSeparator()

        settingsIcon = MYDATA_ICONS.GetIcon("Settings", size="24x24")
        self.settingsTool = addToolMethod(wx.ID_ANY, "Settings",
                                          settingsIcon, shortHelp="Settings")
        self.frame.Bind(wx.EVT_TOOL, self.OnSettings, self.settingsTool)

        self.toolbar.AddSeparator()

        internetIcon = MYDATA_ICONS.GetIcon("Internet explorer", size="24x24")
        self.myTardisTool = addToolMethod(wx.ID_ANY, "MyTardis",
                                          internetIcon, shortHelp="MyTardis")
        self.frame.Bind(wx.EVT_TOOL, self.OnMyTardis, self.myTardisTool)

        self.toolbar.AddSeparator()

        aboutIcon = MYDATA_ICONS.GetIcon("About", size="24x24",
                                         style=IconStyle.HOT)
        self.aboutTool = addToolMethod(wx.ID_ANY, "About MyData",
                                       aboutIcon, shortHelp="About MyData")
        self.frame.Bind(wx.EVT_TOOL, MyData.OnAbout, self.aboutTool)

        self.toolbar.AddSeparator()

        helpIcon = MYDATA_ICONS.GetIcon("Help", size="24x24",
                                        style=IconStyle.HOT)
        self.helpTool = addToolMethod(wx.ID_ANY, "Help", helpIcon,
                                      shortHelp="MyData User Guide")
        self.frame.Bind(wx.EVT_TOOL, MyData.OnHelp, self.helpTool)

        self.toolbar.AddStretchableSpace()
        self.searchCtrl = wx.SearchCtrl(self.toolbar, size=wx.Size(200, -1),
                                        style=wx.TE_PROCESS_ENTER)
        self.searchCtrl.ShowSearchButton(True)
        self.searchCtrl.ShowCancelButton(True)

        self.frame.Bind(wx.EVT_TEXT_ENTER, self.OnDoSearch, self.searchCtrl)
        self.frame.Bind(wx.EVT_TEXT, self.OnDoSearch, self.searchCtrl)

        self.toolbar.AddControl(self.searchCtrl)

        # This basically shows the toolbar
        self.toolbar.Realize()

        # self.SetCallFilterEvent(True)

    # def OnSearchButton(self,event):
        # pass

    # def OnSearchCancel(self,event):
        # pass

    def OnDoSearch(self, event):
        """
        Triggered by user typing into search field in upper-right corner
        or main window.
        """
        if self.tabbedView.GetSelection() == NotebookTabs.FOLDERS:
            self.foldersModel.Filter(event.GetString())
        elif self.tabbedView.GetSelection() == NotebookTabs.USERS:
            self.usersModel.Filter(event.GetString())
        elif self.tabbedView.GetSelection() == NotebookTabs.GROUPS:
            self.groupsModel.Filter(event.GetString())

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
        self.SetShouldAbort(False)
        self.scheduleController.ApplySchedule(event, runManually=True)

    def OnTestRunFromToolbar(self, event):
        """
        The user pressed the Test Run icon on the main window's toolbar.
        """
        logger.debug("OnTestRunFromToolbar")
        self.SetTestRunRunning(True)
        SETTINGS.schedule.scheduleType = "Manually"
        SETTINGS.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.UI_RESPONSE
        self.DisableTestAndUploadToolbarButtons()
        self.testRunFrame.saveButton.Disable()
        self.SetShouldAbort(False)
        self.scheduleController.ApplySchedule(event, runManually=True,
                                              needToValidateSettings=True,
                                              testRun=True)
        self.testRunFrame.Show()
        self.testRunFrame.Clear()
        self.testRunFrame.SetTitle("%s - Test Run" % self.frame.GetTitle())
        logger.testrun("Starting Test Run...")

    def OnRefresh(self, event, needToValidateSettings=True, jobId=None,
                  testRun=False):
        """
        Shut down any existing data folder scan and upload threads,
        validate settings, and begin scanning data folders, checking
        for existing datafiles on MyTardis and uploading any datafiles
        not yet available on MyTardis.
        """
        self.LogOnRefreshCaller(event, jobId)
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

        if (self.ScanningFolders() or self.PerformingLookupsAndUploads()) \
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

        self.searchCtrl.SetValue("")

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
                            wx.CallAfter(EndBusyCursorIfRequired)
                            wx.CallAfter(self.EnableTestAndUploadToolbarButtons)
                            self.SetScanningFolders(False)
                            self.frame.SetStatusMessage(
                                "Settings validation failed.")
                            if testRun:
                                wx.CallAfter(self.GetTestRunFrame().Hide)
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

        if "Group" in SETTINGS.advanced.folderStructure:
            userOrGroup = "user group"
        else:
            userOrGroup = "user"

        self.shouldAbort.clear()

        def WriteProgressUpdateToStatusBar(numUserOrGroupFoldersScanned):
            """
            Write progress update to status bar.
            """
            message = "Scanned %d of %d %s folders" % (
                numUserOrGroupFoldersScanned,
                UsersModel.GetNumUserOrGroupFolders(),
                userOrGroup)
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
            logger.debug("Starting run() method for thread %s"
                         % threading.current_thread().name)
            self.foldersController.InitForUploads()
            message = "Scanning data folders..."
            wx.CallAfter(self.frame.SetStatusMessage, message)
            message = "Scanning data folders in %s..." \
                % SETTINGS.general.dataDirectory
            logger.info(message)
            if testRun:
                logger.testrun(message)
            try:
                self.scanningFoldersThreadingLock.acquire()
                self.SetScanningFolders(True)
                logger.debug("Just set ScanningFolders to True")
                wx.CallAfter(self.DisableTestAndUploadToolbarButtons)
                self.foldersModel.ScanFolders(WriteProgressUpdateToStatusBar,
                                              self.ShouldAbort)
                self.foldersController.FinishedScanningForDatasetFolders()
                self.SetScanningFolders(False)
                self.scanningFoldersThreadingLock.release()
                logger.debug("Just set ScanningFolders to False")
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

            if self.ShouldAbort():
                wx.CallAfter(EndBusyCursorIfRequired)
                wx.CallAfter(self.EnableTestAndUploadToolbarButtons)
                self.SetScanningFolders(False)
                logger.debug("Just set ScanningFolders to False")
                if testRun:
                    logger.testrun("Data scans and uploads were canceled.")
                    self.SetTestRunRunning(False)
                return

            folderStructure = SETTINGS.advanced.folderStructure
            # pylint: disable=too-many-boolean-expressions
            if UsersModel.GetNumUserOrGroupFolders() == 0 or \
                    (folderStructure.startswith("Username") and
                     self.usersModel.GetCount() == 0) or \
                    (folderStructure.startswith("Email") and
                     self.usersModel.GetCount() == 0) or \
                    (folderStructure.startswith("User Group") and
                     self.groupsModel.GetCount() == 0):
                if UsersModel.GetNumUserOrGroupFolders() == 0:
                    message = "No folders were found to upload from."
                else:
                    message = "No valid folders were found to upload from."
                logger.warning(message)
                if testRun:
                    logger.testrun(message)
                wx.CallAfter(self.frame.SetStatusMessage, message)
                wx.CallAfter(self.EnableTestAndUploadToolbarButtons)
                self.SetScanningFolders(False)
                logger.debug("Just set ScanningFolders to False")

            wx.CallAfter(EndBusyCursorIfRequired)
            logger.debug("Finishing run() method for thread %s"
                         % threading.current_thread().name)

        if wx.PyApp.IsMainLoopRunning():
            thread = threading.Thread(target=ScanDataDirs,
                                      name="ScanDataDirectoriesThread")
            logger.debug("OnRefresh: Starting ScanDataDirs thread.")
            thread.start()
            logger.debug("OnRefresh: Started ScanDataDirs thread.")
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
            syncNowMenuItemId = self.taskBarIcon.GetSyncNowMenuItem().GetId()
        except (AttributeError, RuntimeError):
            syncNowMenuItemId = None
        if jobId:
            logger.debug("OnRefresh called from job ID %d" % jobId)
        elif event is None:
            logger.debug("OnRefresh called automatically "
                         "from MyData's OnInit().")
        elif event.GetId() == self.settingsTool.GetId():
            logger.debug("OnRefresh called automatically from "
                         "OnSettings(), after displaying SettingsDialog, "
                         "which was launched from MyData's toolbar.")
        elif event.GetId() == self.uploadTool.GetId():
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
        self.SetShouldAbort(True)
        BeginBusyCursorIfRequired()
        PostEvent(self.foldersController.ShutdownUploadsEvent(canceled=True))
        if event:
            event.Skip()

    def ShouldAbort(self):
        """
        The user has requested aborting the data folder scans and/or
        datafile lookups (verifications) and/or uploads.
        """
        return self.shouldAbort.isSet()

    def SetShouldAbort(self, shouldAbort=True):
        """
        The user has requested aborting the data folder scans and/or
        datafile lookups (verifications) and/or uploads.
        """
        if shouldAbort:
            self.shouldAbort.set()
        else:
            self.shouldAbort.clear()

    def OnOpen(self, event):
        """
        Open the selected data folder in Windows Explorer (Windows) or
        in Finder (Mac OS X).
        """
        if self.tabbedView.GetSelection() == NotebookTabs.FOLDERS:
            self.foldersController.OnOpenFolder(event)

    def OnNotebookPageChanging(self, event):
        """
        Clear the search field after switching views
        (e.g. from Folders to Users).
        """
        if self.searchCtrl:
            self.searchCtrl.SetValue("")

    def OnSettings(self, event, validationMessage=None):
        """
        Open the Settings dialog, which could be in response to the main
        toolbar's Refresh icon, or in response to in response to the task bar
        icon's "MyData Settings" menu item, or in response to MyData being
        launched without any previously saved settings.
        """
        self.SetShouldAbort(False)
        self.frame.SetStatusMessage("")
        settingsDialog = SettingsDialog(self.frame,
                                        size=wx.Size(400, 400),
                                        style=wx.DEFAULT_DIALOG_STYLE,
                                        validationMessage=validationMessage)
        if settingsDialog.ShowModal() == wx.ID_OK:
            logger.debug("settingsDialog.ShowModal() returned wx.ID_OK")
            self.frame.SetTitle("MyData - " + SETTINGS.general.instrumentName)
            self.tasksModel.DeleteAllRows()
            self.scheduleController.ApplySchedule(event)

    def OnMyTardis(self, event):
        """
        Called when user clicks the Internet Browser icon on the
        main toolbar.
        """
        try:
            items = self.foldersView.GetDataViewControl().GetSelections()
            rows = [self.foldersModel.GetRow(item) for item in items]
            if len(rows) == 1:
                folderRecord = self.foldersModel.GetFolderRecord(rows[0])
                if folderRecord.datasetModel is not None:
                    MyData.OpenUrl(SETTINGS.general.myTardisUrl + "/" +
                                   folderRecord.datasetModel.viewUri)
                else:
                    MyData.OpenUrl(SETTINGS.general.myTardisUrl)
            else:
                MyData.OpenUrl(SETTINGS.general.myTardisUrl)
        except:
            logger.error(traceback.format_exc())

    @staticmethod
    def OnHelp(event):
        """
        Called when the user clicks the Help icon on the
        main toolbar.
        """
        new = 2  # Open in a new tab, if possible
        url = "http://mydata.readthedocs.org/en/latest/"
        MyData.OpenUrl(url, new=new)

    @staticmethod
    def OnWalkthrough(event):
        """
        Mac OS X Only.
        Called when the user clicks the Mac OS X Walkthrough
        menu item in the Help menu.
        """
        new = 2  # Open in a new tab, if possible
        url = "http://mydata.readthedocs.org/en/latest/macosx-walkthrough.html"
        MyData.OpenUrl(url, new=new)

    @staticmethod
    def OnAbout(event):
        """
        Called when the user clicks the Info icon on the
        main toolbar.
        """
        msg = "MyData is a desktop application" \
              " for uploading data to MyTardis " \
              "(https://github.com/mytardis/mytardis).\n\n" \
              "MyData is being developed at the Monash e-Research Centre " \
              "(Monash University, Australia)\n\n" \
              "MyData is open source (GPL3) software available from " \
              "https://github.com/mytardis/mydata\n\n" \
              "Version:   " + VERSION + "\n" \
              "Commit:  " + LATEST_COMMIT + "\n"
        dlg = wx.MessageDialog(None, msg, "About MyData",
                               wx.OK | wx.ICON_INFORMATION)
        if wx.PyApp.IsMainLoopRunning():
            dlg.ShowModal()
        else:
            sys.stderr.write("\n%s\n" % msg)

    @staticmethod
    def OpenUrl(url, new=0, autoraise=True):
        """
        Open URL in web browser or just check URL is accessible if running tests.
        """
        if wx.PyApp.IsMainLoopRunning():
            webbrowser.open(url, new, autoraise)
        else:
            response = requests.get(url)
            assert response.status_code == 200

    def GetMainFrame(self):
        """
        Returns the application's main frame, which is
        an instance of MyDataFrame.
        """
        return self.frame

    def GetTestRunFrame(self):
        """
        Returns the Test Run frame, summarizes the
        results of a dry run.
        """
        return self.testRunFrame

    def GetScheduleController(self):
        """
        Returns MyData's schedule controller.
        """
        return self.scheduleController

    def GetConfigPath(self):
        """
        Returns the location on disk of MyData.cfg
        e.g. "C:\\ProgramData\\Monash University\\MyData\\MyData.cfg" or
        "/Users/jsmith/Library/Application Support/MyData/MyData.cfg".
        """
        return self.configPath

    def SetConfigPath(self, configPath):
        """
        Sets the location on disk of MyData.cfg
        e.g. "C:\\ProgramData\\Monash University\\MyData\\MyData.cfg" or
        "/Users/jsmith/Library/Application Support/MyData/MyData.cfg".
        """
        self.configPath = configPath

    def ScanningFolders(self):
        """
        Returns True if MyData is currently scanning data folders.
        """
        return self.scanningFolders.isSet()

    def SetScanningFolders(self, value):
        """
        Records whether MyData is currently scanning data folders.
        """
        if value:
            self.scanningFolders.set()
        else:
            self.scanningFolders.clear()

    def PerformingLookupsAndUploads(self):
        """
        Returns True if MyData is currently performing
        datafile lookups (verifications) and uploading
        datafiles.
        """
        return self.performingLookupsAndUploads.isSet()

    def SetPerformingLookupsAndUploads(self, value):
        """
        Records whether MyData is currently performing
        datafile lookups (verifications) and uploading
        datafiles.
        """
        if value:
            self.performingLookupsAndUploads.set()
        else:
            self.performingLookupsAndUploads.clear()

    def EnableTestAndUploadToolbarButtons(self):
        """
        Enables the Test Run and Upload toolbar buttons,
        indicating that MyData is ready to respond to a
        request to start scanning folders and uploading data.
        """
        self.toolbar.EnableTool(self.stopTool.GetId(), False)
        self.toolbar.EnableTool(self.testTool.GetId(), True)
        self.toolbar.EnableTool(self.uploadTool.GetId(), True)

    def DisableTestAndUploadToolbarButtons(self):
        """
        Disables the Test Run and Upload toolbar buttons,
        indicating that MyData is busy scanning folders,
        uploading data, validating settings or performing
        a test run.
        """
        self.toolbar.EnableTool(self.stopTool.GetId(), True)
        self.toolbar.EnableTool(self.testTool.GetId(), False)
        self.toolbar.EnableTool(self.uploadTool.GetId(), False)

    def Processing(self):
        """
        Returns True/False, depending on whether MyData is
        currently busy processing something.
        """
        try:
            return self.toolbar.GetToolEnabled(self.stopTool.GetId())
        except wx.PyDeadObjectError:
            return False

    def TestRunRunning(self):
        """
        Called when the Test Run window is closed to determine
        whether the Test Run is still running.  If so, it will
        be aborted.  If not, we need to be careful to avoid
        aborting a real uploads run.
        """
        return self.testRunRunning.isSet()

    def SetTestRunRunning(self, value):
        """
        Records whether MyData is currently performing a test run.
        """
        if value:
            self.testRunRunning.set()
        else:
            self.testRunRunning.clear()


def Run(argv):
    """
    Main function for launching MyData.
    """
    app = MyData(argv)
    app.MainLoop()


if __name__ == "__main__":
    sys.stderr.write(
        "Please use run.py in MyData.py's parent directory instead.\n")

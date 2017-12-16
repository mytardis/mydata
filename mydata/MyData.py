"""
MyData.py

Main module for MyData.

To run MyData from the command-line, use "python run.py", where run.py is
in the parent directory of the directory containing MyData.py.
"""
import os
import sys

import wx

from . import __version__ as VERSION
from . import LATEST_COMMIT
from .constants import APPNAME
from .settings import SETTINGS

from .dataviewmodels.dataview import DATAVIEW_MODELS

from .views.mydata import MyDataFrame
from .views.testrun import TestRunFrame

from .controllers.folders import FoldersController
from .controllers.schedule import ScheduleController
from .controllers.updates import VersionCheck

from .events.settings import OnSettings
from .events import MYDATA_EVENTS

from .utils.notification import Notification

from .logs import logger


class MyData(wx.App):
    """
    Encapsulates the MyData application.
    """
    def __init__(self, argv):
        """
        __init__ is run before OnInit.

        :param argv: Command-line arguments or mock arguments from unittests
        """
        self.instance = None

        self.frame = None

        # The Test Run frame summarizes the results of a dry run:
        self.testRunFrame = None

        self.foldersController = None
        self.scheduleController = None

        MyData.ParseArgs(argv)

        wx.App.__init__(self, redirect=False)

    @staticmethod
    def ParseArgs(argv):
        """
        Parse command-line arguments.
        """
        import argparse
        import logging

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
        from .utils import CreateConfigPathIfNecessary
        from .utils import InitializeTrustedCertsPath
        from .utils import CheckIfSystemTrayFunctionalityMissing
        self.SetAppName(APPNAME)
        appdirPath = CreateConfigPathIfNecessary()
        InitializeTrustedCertsPath()
        InitializeDataViewModels()
        self.frame = MyDataFrame()

        # Wait until views have been created (in MyDataFrame) before doing
        # logging, so that the logged messages will appear in the Log View:
        logger.info("%s version: v%s" % (APPNAME, VERSION))
        logger.info("%s commit:  %s" % (APPNAME, LATEST_COMMIT))
        logger.info("appdirPath: " + appdirPath)
        logger.info("SETTINGS.configPath: " + SETTINGS.configPath)

        VersionCheck()

        self.frame.Bind(wx.EVT_ACTIVATE_APP, self.OnActivateApp)
        MYDATA_EVENTS.InitializeWithNotifyWindow(self.frame)
        self.testRunFrame = TestRunFrame(self.frame)

        self.foldersController = FoldersController(self.frame)
        self.scheduleController = ScheduleController()

        if sys.platform.startswith("win"):
            self.CheckIfAlreadyRunning(appdirPath)

        self.SetTopWindow(self.frame)

        if sys.platform.startswith("linux"):
            CheckIfSystemTrayFunctionalityMissing()

        event = None
        if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ and \
                SETTINGS.RequiredFieldIsBlank():
            self.frame.Show(True)
            OnSettings(event)
        else:
            self.frame.SetTitle(
                "%s - %s" % (APPNAME, SETTINGS.general.instrumentName))
            self.frame.Hide()
            if sys.platform.startswith("darwin"):
                message = \
                    "Click the MyData menubar icon to access its menu."
            else:
                message = \
                    "Click the MyData system tray icon to access its menu."
            # Use CallAfter here to ensure this is called after the main loop
            # has started, because we've occasionally seen errors like this:
            # wx._core.PyAssertionError: C++ assertion "m_iconAdded" failed at
            # ..\..\src\msw\taskbar.cpp(255) in wxTaskBarIcon::ShowBalloon():
            # can't be used before the icon is created
            wx.CallAfter(Notification.Notify, message, title=APPNAME)
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
            if 'MYDATA_TESTING' not in os.environ:
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

    def ShutDownCleanlyAndExit(self, event, confirm=True):
        """
        Shut down MyData cleanly and quit.
        """
        from .utils import BeginBusyCursorIfRequired
        from .utils import EndBusyCursorIfRequired
        if sys.platform.startswith("linux"):
            from .linuxsubprocesses import StopErrandBoy

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
            DATAVIEW_MODELS['tasks'].ShutDown()
            if sys.platform.startswith("linux"):
                StopErrandBoy()
            # sys.exit can raise exceptions if the wx.App
            # is shutting down:
            os._exit(0)  # pylint: disable=protected-access

    def Processing(self):
        """
        Returns True/False, depending on whether MyData is
        currently busy processing something.
        """
        try:
            return self.frame.toolbar.GetToolEnabled(
                self.frame.toolbar.stopTool.GetId())
        except wx.PyDeadObjectError:  # Exception no longer exists in Phoenix.
            return False


def InitializeDataViewModels():
    """
    Initialize data view models
    """
    from .dataviewmodels.users import UsersModel
    from .dataviewmodels.groups import GroupsModel
    from .dataviewmodels.verifications import VerificationsModel
    from .dataviewmodels.uploads import UploadsModel
    from .dataviewmodels.tasks import TasksModel
    from .dataviewmodels.folders import FoldersModel
    DATAVIEW_MODELS['users'] = UsersModel()
    DATAVIEW_MODELS['groups'] = GroupsModel()
    DATAVIEW_MODELS['verifications'] = VerificationsModel()
    DATAVIEW_MODELS['uploads'] = UploadsModel()
    DATAVIEW_MODELS['tasks'] = TasksModel()
    DATAVIEW_MODELS['folders'] = FoldersModel()


def Run(argv):
    """
    Main function for launching MyData.
    """
    app = MyData(argv)
    app.MainLoop()


if __name__ == "__main__":
    sys.stderr.write(
        "Please use run.py in MyData.py's parent directory instead.\n")

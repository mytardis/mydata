"""
This package contains tests to be run with "nosetests".

On Windows, tests are run automatically for every commit, thanks to AppVeyor.
    See: appveyor.yml

On Linux, tests are run automatically for every commit, thanks to Travis CI.
    See: .travis.yml

On Mac OS X, tests can be run manually with:
    python setup.py nosetests
Coverage can be reported with:
    coverage report -m
and coverage can be uploaded with:
    codecov -X gcov

"python setup.py nosetests" generates a .coverage file, which is necessary to
run "coverage report -m".  It should be removed before subsequent runs of
"python setup.py nosetests" to ensure that recently deleted lines of code
are not included.

Similarly, coverage.xml (generated by "codecov") should be removed before
subsequent "codecov" runs to ensure an accurate coverage report.
"""
import os
import sys
import tempfile
import threading
import unittest

import wx

from ..events import MYDATA_EVENTS
from ..settings import SETTINGS
from ..threads.flags import FLAGS
from ..models.settings import SettingsModel
from ..models.settings.validation import ValidateSettings
from ..dataviewmodels.dataview import DATAVIEW_MODELS
from ..dataviewmodels.folders import FoldersModel
from ..dataviewmodels.users import UsersModel
from ..dataviewmodels.groups import GroupsModel
from .utils import StartFakeMyTardisServer
from .utils import WaitForFakeMyTardisServerToStart
if sys.platform.startswith("linux"):
    from ..linuxsubprocesses import StopErrandBoy


class MyApp(wx.App):
    """
    App class to fix following issue with wxPython 4.1.0:
    https://discuss.wxpython.org/t/what-is-wxpython-doing-to-the-locale-to-makes-pandas-crash/34606/22
    """
    def InitLocale(self):
        self.ResetLocale()


class MyDataMinimalTester(unittest.TestCase):
    """
    Lightweight class to derive from for tests requiring the
    MYDATA_TESTING environment variable to be set.
    """
    def setUp(self):
        os.environ['MYDATA_TESTING'] = 'True'
        os.environ['MYDATA_DONT_SHOW_MODAL_DIALOGS'] = 'True'

    def tearDown(self):
        del os.environ['MYDATA_TESTING']
        del os.environ['MYDATA_DONT_SHOW_MODAL_DIALOGS']


class MockToolbar(object):
    """
    Mock toolbar for unit tests
    """
    def EnableTestAndUploadToolbarButtons(self):
        """
        Mock method for unit tests
        """
        assert self  # Avoid no-self-use complaints from Pylint
        sys.stderr.write("Enabling Test and Upload Toolbar Buttons.\n")


class TestFrame(wx.Frame):
    """
    Simple main window class for unit tests.
    """
    def __init__(self, parent, title):
        self.parent = parent
        self.title = title
        self.toolbar = MockToolbar()
        super(TestFrame, self).__init__(parent=parent, title=title)

    def SetStatusMessage(self, msg, force=False):
        """
        Mock status bar updating method for unit tests.
        """
        if force:
            suffix = " (forcefully updated)"
        else:
            suffix = ""
        sys.stderr.write("%s STATUS: %s%s\n" % (self.GetTitle(), msg, suffix))


class MyDataTester(unittest.TestCase):
    """
    Base class for inheriting from for tests requiring a fake MyTardis server
    """
    def __init__(self, *args, **kwargs):
        super(MyDataTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.fakeMyTardisUrl = None

    def setUp(self):
        """
        Initialize test environment including a fake MyTardis server
        """
        os.environ['MYDATA_TESTING'] = 'True'
        os.environ['MYDATA_DONT_SHOW_MODAL_DIALOGS'] = 'True'
        FLAGS.shouldAbort = False
        FLAGS.testRunRunning = False
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        WaitForFakeMyTardisServerToStart(self.fakeMyTardisUrl)
        InitializeModels()

    def tearDown(self):
        del os.environ['MYDATA_TESTING']
        del os.environ['MYDATA_DONT_SHOW_MODAL_DIALOGS']

        if self.httpd:
            self.httpd.shutdown()
        if self.fakeMyTardisServerThread:
            self.fakeMyTardisServerThread.join()
        if sys.platform.startswith("linux"):
            StopErrandBoy()

    def UpdateSettingsFromCfg(self, configName, dataFolderName=None):
        """
        Update the global settings instance from a test MyData.cfg file and
        update the dataDirectory and myTardisUrl for the test environment.
        """
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/%s.cfg" % configName)
        try:
            self.assertTrue(os.path.exists(pathToTestConfig))
        except AssertionError:
            sys.stderr.write("Config path: %s\n" % pathToTestConfig)
            raise
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        if not dataFolderName:
            dataFolderName = configName
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata", dataFolderName)
        try:
            self.assertTrue(os.path.exists(dataDirectory))
        except AssertionError:
            sys.stderr.write("Data directory: %s\n" % dataDirectory)
            raise
        SETTINGS.general.dataDirectory = dataDirectory
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        SETTINGS.miscellaneous.cacheDataFileLookups = False

    def AssertUsers(self, users):
        """
        Check the users in self.usersModel
        """
        self.assertEqual(
            sorted(DATAVIEW_MODELS['users'].GetValuesForColname("Username")),
            users)

    def AssertFolders(self, folders):
        """
        Check the folders in DATAVIEW_MODELS['folders']
        """
        folderNames = []
        for row in range(DATAVIEW_MODELS['folders'].GetRowCount()):
            folderNames.append(
                DATAVIEW_MODELS['folders'].GetFolderRecord(row).folderName)
        self.assertEqual(sorted(folderNames), folders)

    def AssertNumFiles(self, numFiles):
        """
        Check the number of files found in DATAVIEW_MODELS['folders']
        """
        totalFiles = 0
        for row in range(DATAVIEW_MODELS['folders'].GetRowCount()):
            totalFiles += DATAVIEW_MODELS['folders'] \
                .GetFolderRecord(row).numFiles
        self.assertEqual(totalFiles, numFiles)


class MyDataGuiTester(MyDataTester):
    """
    Base class for inheriting from for tests requiring a fake MyTardis server
    and a wxPython GUI application
    """
    def __init__(self, *args, **kwargs):
        super(MyDataGuiTester, self).__init__(*args, **kwargs)
        self.app = None

    def setUp(self):
        """
        Initialize test environment including a fake MyTardis server,
        and a wxPython app and main frame
        """
        from mydata.logs import logger
        super(MyDataGuiTester, self).setUp()
        self.app = MyApp()
        self.app.frame = TestFrame(None, self.shortDescription())
        MYDATA_EVENTS.InitializeWithNotifyWindow(self.app.frame)
        logger.loggerObject.removeHandler(logger.logWindowHandler)

    def tearDown(self):
        super(MyDataGuiTester, self).tearDown()
        if self.app and self.app.frame:
            self.app.frame.Close(force=True)
        if self.app:
            self.app.MainLoop()
            for thread in threading.enumerate():
                if thread.name != "MainThread":
                    sys.stderr.write(
                        "MyDataGuiTester.tearDown: Thread still running: %s\n" % thread.name)
            del self.app
            self.assertIsNone(wx.GetApp())


class MyDataSettingsTester(MyDataGuiTester):
    """
    Base class for inheriting from for tests requiring a fake MyTardis server
    """
    def __init__(self, *args, **kwargs):
        super(MyDataSettingsTester, self).__init__(*args, **kwargs)
        # Used for saving MyData.cfg:
        self.tempFilePath = None

    def setUp(self):
        super(MyDataSettingsTester, self).setUp()
        with tempfile.NamedTemporaryFile() as tempConfig:
            self.tempFilePath = tempConfig.name

    def tearDown(self):
        if os.path.exists(self.tempFilePath):
            os.remove(self.tempFilePath)
        super(MyDataSettingsTester, self).tearDown()

    def UpdateSettingsFromCfg(self, configName, dataFolderName=None):
        """
        Update the global settings instance from a test MyData.cfg file and
        update the dataDirectory and myTardisUrl for the test environment.
        """
        super(MyDataSettingsTester, self).UpdateSettingsFromCfg(
            configName, dataFolderName)
        SETTINGS.configPath = self.tempFilePath


class MyDataScanFoldersTester(MyDataGuiTester):
    """
    Base class for inheriting from for tests requiring a fake MyTardis server

    Includes callbacks used by ScanFolders.
    """
    @staticmethod
    def ProgressCallback(numUserOrGroupFoldersScanned):
        """
        Callback for ScanFolders.
        """
        assert numUserOrGroupFoldersScanned > 0


def InitializeModels():
    """
    Initialize dataview models.

    Should be called after loading valid settings.
    """
    if 'users' in DATAVIEW_MODELS:
        DATAVIEW_MODELS['users'].DeleteAllRows()
    else:
        DATAVIEW_MODELS['users'] = UsersModel()
    if 'groups' in DATAVIEW_MODELS:
        DATAVIEW_MODELS['groups'].DeleteAllRows()
    else:
        DATAVIEW_MODELS['groups'] = GroupsModel()
    if 'folders' in DATAVIEW_MODELS:
        DATAVIEW_MODELS['folders'].DeleteAllRows()
    else:
        DATAVIEW_MODELS['folders'] = FoldersModel()


def ValidateSettingsAndScanFolders():
    """
    Collecting some common code needed by multiple "scan folders" tests
    """
    ValidateSettings()
    DATAVIEW_MODELS['folders'].ScanFolders(
        MyDataScanFoldersTester.ProgressCallback)

"""
Test ability to use MyData's Test Run.
"""
import os
import sys
import tempfile
import unittest

import wx

from ...MyData import MyData
from ...events import MYDATA_EVENTS
from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from ..utils import StartFakeMyTardisServer
from ..utils import WaitForFakeMyTardisServerToStart
if sys.platform.startswith("linux"):
    from ...linuxsubprocesses import StopErrandBoy


class MyDataAppInstanceTester(unittest.TestCase):
    """
    Test ability to use MyData's Test Run.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(MyDataAppInstanceTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.mydataApp = None

    def setUp(self):
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = SettingsModel(configPath=configPath, checkForUpdates=False)
        self.tempConfig = tempfile.NamedTemporaryFile()
        self.tempFilePath = self.tempConfig.name
        self.tempConfig.close()
        self.settingsModel.configPath = self.tempFilePath
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.settingsModel.general.myTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        self.settingsModel.general.dataDirectory = dataDirectory
        SaveSettingsToDisk(self.settingsModel)

    def test_mydata_test_run(self):
        """
        Test ability to use MyData's Test Run.
        """
        WaitForFakeMyTardisServerToStart(self.settingsModel.general.myTardisUrl)
        ValidateSettings(self.settingsModel)
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'],
                                settingsModel=self.settingsModel)

        popupMenu = self.mydataApp.taskBarIcon.CreatePopupMenu()

        # Just for test coverage:
        self.mydataApp.LogOnRefreshCaller(event=None, jobId=1)
        self.mydataApp.LogOnRefreshCaller(event=None, jobId=None)
        pyEvent = wx.PyEvent()
        jobId = None
        pyEvent.SetId(self.mydataApp.settingsTool.GetId())
        self.mydataApp.LogOnRefreshCaller(pyEvent, jobId)
        pyEvent.SetId(self.mydataApp.uploadTool.GetId())
        self.mydataApp.LogOnRefreshCaller(pyEvent, jobId)
        # Requires popupMenu (defined above):
        pyEvent.SetId(self.mydataApp.taskBarIcon.GetSyncNowMenuItem().GetId())
        self.mydataApp.LogOnRefreshCaller(pyEvent, jobId)
        mydataEvent = MYDATA_EVENTS.ValidateSettingsForRefreshEvent()
        self.mydataApp.LogOnRefreshCaller(mydataEvent, jobId)
        mydataEvent = MYDATA_EVENTS.SettingsValidationCompleteEvent()
        self.mydataApp.LogOnRefreshCaller(mydataEvent, jobId)
        mydataEvent = MYDATA_EVENTS.ShutdownForRefreshCompleteEvent()
        self.mydataApp.LogOnRefreshCaller(mydataEvent, jobId)
        mydataEvent = MYDATA_EVENTS.SettingsValidationCompleteEvent()
        self.mydataApp.LogOnRefreshCaller(mydataEvent, jobId)
        pyEvent = wx.PyEvent()
        pyEvent.SetEventType(12345)
        self.mydataApp.LogOnRefreshCaller(pyEvent, jobId)

        popupMenu.Destroy()

        # Test opening webpages using fake MyTardis URL.
        pyEvent = wx.PyEvent()
        self.mydataApp.OnMyTardis(pyEvent)
        self.mydataApp.OnAbout(pyEvent)

        # When running MyData without an event loop, this will block until complete:
        self.mydataApp.OnTestRunFromToolbar(event=wx.PyEvent())

    def tearDown(self):
        self.mydataApp.GetTestRunFrame().Hide()
        self.mydataApp.GetMainFrame().Hide()
        self.mydataApp.GetMainFrame().Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()
        if os.path.exists(self.tempFilePath):
            os.remove(self.tempFilePath)
        if sys.platform.startswith("linux"):
            StopErrandBoy()

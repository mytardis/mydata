"""
Test ability to use MyData's Test Run.
"""
import os

import wx

from ...settings import SETTINGS
from ...MyData import MyData
from ...events import MYDATA_EVENTS
from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


class MyDataAppInstanceTester(MyDataSettingsTester):
    """
    Test ability to use MyData's Test Run.
    """
    def __init__(self, *args, **kwargs):
        super(MyDataAppInstanceTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(MyDataAppInstanceTester, self).setUp()
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        SETTINGS.Update(
            SettingsModel(configPath=configPath, checkForUpdates=False))
        SETTINGS.configPath = self.tempFilePath
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SaveSettingsToDisk()

    def test_mydata_test_run(self):
        """
        Test ability to use MyData's Test Run.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])

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
        super(MyDataAppInstanceTester, self).tearDown()
        self.mydataApp.GetTestRunFrame().Hide()
        self.mydataApp.GetMainFrame().Hide()
        self.mydataApp.GetMainFrame().Destroy()

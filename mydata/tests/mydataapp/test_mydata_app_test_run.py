"""
Test ability to use MyData's Test Run.
"""
import wx

from ...MyData import MyData
from ...events import MYDATA_EVENTS
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
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        SaveSettingsToDisk()

    def test_mydata_test_run(self):
        """
        Test ability to use MyData's Test Run.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])

        popupMenu = self.mydataApp.frame.taskBarIcon.CreatePopupMenu()

        # Just for test coverage:
        self.mydataApp.LogOnRefreshCaller(event=None, jobId=1)
        self.mydataApp.LogOnRefreshCaller(event=None, jobId=None)
        pyEvent = wx.PyEvent()
        jobId = None
        toolbar = self.mydataApp.frame.toolbar
        pyEvent.SetId(toolbar.settingsTool.GetId())
        self.mydataApp.LogOnRefreshCaller(pyEvent, jobId)
        pyEvent.SetId(toolbar.uploadTool.GetId())
        self.mydataApp.LogOnRefreshCaller(pyEvent, jobId)
        # Requires popupMenu (defined above):
        pyEvent.SetId(
            self.mydataApp.frame.taskBarIcon.GetSyncNowMenuItem().GetId())
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
        self.mydataApp.frame.OnMyTardis(pyEvent)
        self.mydataApp.frame.OnAbout(pyEvent)

        # When running MyData without an event loop, this will block until complete:
        self.mydataApp.OnTestRunFromToolbar(event=wx.PyEvent())

    def tearDown(self):
        super(MyDataAppInstanceTester, self).tearDown()
        self.mydataApp.testRunFrame.Hide()
        self.mydataApp.frame.Hide()
        self.mydataApp.frame.Destroy()

"""
Test ability to use MyData's Test Run.
"""
import unittest
from mock import patch

import wx

from ...MyData import MyData
from ...events import MYDATA_EVENTS
from ...events.start import LogStartScansAndUploadsCaller
from ...events.start import OnTestRunFromToolbar
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from ...settings import SETTINGS
from .. import MyDataSettingsTester


@unittest.skip("Needs rewriting since MainLoop() has been added to tearDown")
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
        """Test ability to use MyData's Test Run.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])

        popupMenu = self.mydataApp.frame.taskBarIcon.CreatePopupMenu()

        # Just for test coverage:
        LogStartScansAndUploadsCaller(event=None, jobId=1)
        LogStartScansAndUploadsCaller(event=None, jobId=None)
        pyEvent = wx.PyEvent()
        jobId = None
        toolbar = self.mydataApp.frame.toolbar
        pyEvent.SetId(toolbar.settingsTool.GetId())
        LogStartScansAndUploadsCaller(pyEvent, jobId)
        pyEvent.SetId(toolbar.uploadTool.GetId())
        LogStartScansAndUploadsCaller(pyEvent, jobId)
        # Requires popupMenu (defined above):
        pyEvent.SetId(
            self.mydataApp.frame.taskBarIcon.GetSyncNowMenuItem().GetId())
        LogStartScansAndUploadsCaller(pyEvent, jobId)
        mydataEvent = MYDATA_EVENTS.ValidateSettingsForRefreshEvent()
        LogStartScansAndUploadsCaller(mydataEvent, jobId)
        mydataEvent = MYDATA_EVENTS.SettingsValidationCompleteEvent()
        LogStartScansAndUploadsCaller(mydataEvent, jobId)
        mydataEvent = MYDATA_EVENTS.ShutdownForRefreshCompleteEvent()
        LogStartScansAndUploadsCaller(mydataEvent, jobId)
        mydataEvent = MYDATA_EVENTS.SettingsValidationCompleteEvent()
        LogStartScansAndUploadsCaller(mydataEvent, jobId)
        pyEvent = wx.PyEvent()
        pyEvent.SetEventType(12345)
        LogStartScansAndUploadsCaller(pyEvent, jobId)

        popupMenu.Destroy()

        # Test opening MyTardis webpage using fake MyTardis URL:
        pyEvent = wx.PyEvent()
        with patch("webbrowser.open") as mockWebbrowserOpen:
            self.mydataApp.frame.OnMyTardis(pyEvent)
            mockWebbrowserOpen.assert_called_once_with(
                SETTINGS.general.myTardisUrl, 0, True)

        # Test opening About dialog:
        self.mydataApp.frame.OnAbout(pyEvent)

        # When running MyData without an event loop, this will block until complete:
        OnTestRunFromToolbar(event=wx.PyEvent())

    def tearDown(self):
        super(MyDataAppInstanceTester, self).tearDown()
        self.mydataApp.testRunFrame.Hide()
        self.mydataApp.frame.Hide()

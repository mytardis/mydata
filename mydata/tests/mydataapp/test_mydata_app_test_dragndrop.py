"""
Test ability to use MyData's Test Run when a file is dragged and dropped.
"""
import wx

from ...MyData import MyData
from ...events import MYDATA_EVENTS
from ...events.start import LogStartScansAndUploadsCaller
from ...events.start import OnTestRunFromToolbar
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from ...models.settings.general import GeneralSettingsModel # why isn't this initialising? 
from .. import MyDataSettingsTester
from ...settings import SETTINGS

class MyDataAppInstanceDragnDropTester(MyDataSettingsTester):
    """
    Test ability to use MyData's Test Run when a file is dragged and dropped.
    """
    def __init__(self, *args, **kwargs):
        super(MyDataAppInstanceDragnDropTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(MyDataAppInstanceDragnDropTester, self).setUp()
        #self.UpdateSettingsFromCfg(
        #    "testdataDragnDropDataset",
        #    dataFolderName="testdataDragnDropDataset")
        #SaveSettingsToDisk()
        return

    def test_mydata_test_run(self):
        """
        Test ability to use MyData's Test Run when a file is dragged and dropped.
        """
        #ValidateSettings()
        self.settingsModel = GeneralSettingsModel() # Not initialising properly?
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

        # Test opening webpages using fake MyTardis URL.
        pyEvent = wx.PyEvent()
        self.mydataApp.frame.OnMyTardis(pyEvent)
        self.mydataApp.frame.OnAbout(pyEvent)

        # Test drag-n-drop functionality
        #self.mydataApp.frame.panel.GetDropTarget().OnDropFiles(0,0,[self.settingsModel.dataDirectory()]) 
        # WHY DOESN'T THIS WORK?
        dropTarget=self.mydataApp.frame.panel.GetDropTarget()
        dropTarget.OnDropFiles(0,0,[SETTINGS.general.dataDirectory])
        dropTarget.dlg.emailEntry.SetValue(r'testuser1@example.com')
        dropTarget.dlg.OnUpload(wx.PyCommandEvent(wx.EVT_BUTTON.typeId, dropTarget.dlg.GetId()))
        dropTarget.dlg.EndModal(wx.ID_CLOSE)

        # When running MyData without an event loop, this will block until complete:
        OnTestRunFromToolbar(event=wx.PyEvent())

    def tearDown(self):
        super(MyDataAppInstanceDragnDropTester, self).tearDown()
        #self.mydataApp.testRunFrame.Hide()
        #self.mydataApp.frame.Hide()
        #self.mydataApp.frame.Destroy()


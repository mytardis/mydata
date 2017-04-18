"""
Test On Settings Saved schedule type.
"""
import wx

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...models.settings import LastSettingsUpdateTrigger
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


class OnSettingsSavedScheduleTester(MyDataSettingsTester):
    """
    Test On Settings Saved schedule type.
    """
    def __init__(self, *args, **kwargs):
        super(OnSettingsSavedScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(OnSettingsSavedScheduleTester, self).setUp()
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        SETTINGS.schedule.scheduleType = "On Settings Saved"
        SaveSettingsToDisk()

    def test_on_settings_saved_schedule(self):
        """
        Test On Settings Saved schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        self.mydataApp.frame.taskBarIcon.CreatePopupMenu()
        pyEvent = wx.PyEvent()
        SETTINGS.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.UI_RESPONSE
        # Having set SETTINGS.lastSettingsUpdateTrigger to
        # LastSettingsUpdateTrigger.UI_RESPONSE, MyData's settings validation
        # will assume that the settings came from MyData's interactive settings
        # dialog, so it will check whether MyData is set to start
        # automatically, but we can do this to save time:
        SETTINGS.lastCheckedAutostartValue = \
            SETTINGS.advanced.startAutomaticallyOnLogin
        self.mydataApp.scheduleController.ApplySchedule(pyEvent)
        SETTINGS.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.READ_FROM_DISK
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        uploadsModel = self.mydataApp.dataViewModels['uploads']
        self.assertEqual(uploadsModel.GetCompletedCount(), 7)
        self.assertIn(
            ("CreateOnSettingsSavedTask - MainThread - DEBUG - "
             "Schedule type is On Settings Saved"),
            logger.loggerOutput.getvalue())

"""
Test On Settings Saved schedule type.
"""
import os

import wx

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...models.settings import SettingsModel
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
        SETTINGS.schedule.scheduleType = "On Settings Saved"
        SETTINGS.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.UI_RESPONSE
        SaveSettingsToDisk()

    def test_on_settings_saved_schedule(self):
        """
        Test On Settings Saved schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        self.mydataApp.taskBarIcon.CreatePopupMenu()
        pyEvent = wx.PyEvent()
        self.mydataApp.scheduleController.ApplySchedule(pyEvent)
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 7)
        self.assertIn(
            ("CreateOnSettingsSavedTask - MainThread - DEBUG - "
             "Schedule type is On Settings Saved"),
            logger.loggerOutput.getvalue())
    def tearDown(self):
        super(OnSettingsSavedScheduleTester, self).tearDown()
        self.mydataApp.GetMainFrame().Hide()
        self.mydataApp.GetMainFrame().Destroy()

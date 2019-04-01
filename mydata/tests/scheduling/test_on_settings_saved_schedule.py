"""
Test On Settings Saved schedule type.
"""
import unittest

import six
import wx

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...models.settings import LastSettingsUpdateTrigger
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


@unittest.skipIf(six.PY3, "Not working in Python 3 yet")
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

    def tearDown(self):
        super(OnSettingsSavedScheduleTester, self).tearDown()
        self.mydataApp.frame.Hide()
        self.mydataApp.frame.Destroy()

    def test_on_settings_saved_schedule(self):
        """Test On Settings Saved schedule type
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        self.mydataApp.frame.taskBarIcon.CreatePopupMenu()
        pyEvent = wx.PyEvent()
        SETTINGS.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.UI_RESPONSE
        self.mydataApp.scheduleController.ApplySchedule(pyEvent)
        SETTINGS.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.READ_FROM_DISK
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        uploadsModel = DATAVIEW_MODELS['uploads']
        self.assertEqual(uploadsModel.GetCompletedCount(), 8)
        self.assertIn(
            ("CreateOnSettingsSavedTask - MainThread - DEBUG - "
             "Schedule type is On Settings Saved"),
            logger.loggerOutput.getvalue())

"""
Test Manual schedule type.
"""
import wx

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...models.settings import LastSettingsUpdateTrigger
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


class ManualScheduleTester(MyDataSettingsTester):
    """
    Test Manual schedule type.
    """
    def __init__(self, *args, **kwargs):
        super(ManualScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(ManualScheduleTester, self).setUp()
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        SETTINGS.schedule.scheduleType = "Manually"
        SaveSettingsToDisk()

    def test_manual_schedule(self):
        """
        Test Manual schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        # If schedule type is "Manually", it will only run in response to a
        # User Interface response, so we'll set
        # SETTINGS.lastSettingsUpdateTrigger to simulate a UI trigger:
        SETTINGS.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.UI_RESPONSE
        pyEvent = wx.PyEvent()
        self.mydataApp.scheduleController.ApplySchedule(pyEvent,
                                                        runManually=True)
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        uploadsModel = DATAVIEW_MODELS['uploads']
        self.assertEqual(uploadsModel.GetCompletedCount(), 7)
        self.assertIn(
            "ApplySchedule - MainThread - DEBUG - Schedule type is Manually",
            logger.loggerOutput.getvalue())

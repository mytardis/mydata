"""
Test Daily schedule type.
"""
from datetime import datetime
from datetime import timedelta

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


class DailyScheduleTester(MyDataSettingsTester):
    """
    Test Daily schedule type.
    """
    def __init__(self, *args, **kwargs):
        super(DailyScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(DailyScheduleTester, self).setUp()
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        SETTINGS.schedule.scheduleType = "Daily"
        SETTINGS.schedule.scheduledTime = \
            datetime.time(datetime.now().replace(microsecond=0) +
                          timedelta(minutes=1))
        SaveSettingsToDisk()

    def test_daily_schedule(self):
        """
        Test Daily schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])

        self.assertTrue(SETTINGS.advanced.uploadInvalidUserOrGroupFolders)
        uploadsModel = self.mydataApp.dataViewModels['uploads']
        self.assertEqual(uploadsModel.GetCompletedCount(), 7)
        self.assertIn(
            "CreateDailyTask - MainThread - DEBUG - Schedule type is Daily",
            logger.loggerOutput.getvalue())
        # TO DO: A way of testing that additional tasks are scheduled,
        # according to the timer interval.

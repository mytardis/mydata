"""
Test Daily schedule type.
"""
from datetime import datetime
from datetime import timedelta
import unittest

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


@unittest.skip("Needs rewriting since MainLoop() has been added to tearDown")
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

    def test_daily_schedule(self):
        """Test Daily schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])

        self.assertTrue(SETTINGS.advanced.uploadInvalidUserOrGroupFolders)
        uploadsModel = DATAVIEW_MODELS['uploads']
        self.assertEqual(uploadsModel.GetCompletedCount(), 8)
        self.assertIn(
            "CreateDailyTask - MainThread - DEBUG - Schedule type is Daily",
            logger.loggerOutput.getvalue())
        # TO DO: A way of testing that additional tasks are scheduled,
        # according to the timer interval.

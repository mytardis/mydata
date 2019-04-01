"""
Test ability to read and validate scheduling config.
"""
import unittest
from datetime import datetime

import six

from ...settings import SETTINGS
from ...models.settings.validation import ValidateSettings
from .. import MyDataTester


@unittest.skipIf(six.PY3, "Not working in Python 3 yet")
class SchedulingConfigTester(MyDataTester):
    """
    Test ability to read and validate scheduling config.
    """
    def test_read_timer_cfg(self):
        """Test ability to read Timer settings from MyData.cfg
        """
        self.UpdateSettingsFromCfg(
            "testdataTimer",
            dataFolderName="testdataDataset")
        self.assertEqual(SETTINGS.schedule.scheduleType, "Timer")
        self.assertEqual(SETTINGS.schedule.timerMinutes, 15)
        timerFromTime = \
            datetime.time(datetime.strptime("00:00:00", "%H:%M:%S"))
        self.assertEqual(SETTINGS.schedule.timerFromTime, timerFromTime)
        timerToTime = \
            datetime.time(datetime.strptime("23:59:00", "%H:%M:%S"))
        self.assertEqual(SETTINGS.schedule.timerToTime, timerToTime)
        ValidateSettings()

    def test_read_weekly_cfg(self):
        """Test ability to read Weekly schedule settings from MyData.cfg
        """
        self.UpdateSettingsFromCfg(
            "testdataWeekly",
            dataFolderName="testdataDataset")
        self.assertEqual(SETTINGS.schedule.scheduleType, "Weekly")
        self.assertEqual(SETTINGS.schedule.mondayChecked, True)
        self.assertEqual(SETTINGS.schedule.tuesdayChecked, False)
        ValidateSettings()

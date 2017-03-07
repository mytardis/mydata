"""
Test ability to read and validate scheduling config.
"""
from datetime import datetime
import os

from ...settings import SETTINGS
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from .. import MyDataTester


class SchedulingConfigTester(MyDataTester):
    """
    Test ability to read and validate scheduling config.
    """
    def setUp(self):
        super(SchedulingConfigTester, self).setUp()
        super(SchedulingConfigTester, self).InitializeAppAndFrame(
            'SchedulingConfigTester')

    def test_read_timer_cfg(self):
        """
        Test ability to read Timer settings from MyData.cfg
        """
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataTimer.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
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
        """
        Test ability to read Weekly schedule settings from MyData.cfg
        """
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataWeekly.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        self.assertEqual(SETTINGS.schedule.scheduleType, "Weekly")
        self.assertEqual(SETTINGS.schedule.mondayChecked, True)
        self.assertEqual(SETTINGS.schedule.tuesdayChecked, False)
        ValidateSettings()

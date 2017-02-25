"""
Test ability to read and validate scheduling config.
"""
from datetime import datetime
import os

from .. import MyDataTester
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings


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
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        self.assertEqual(settingsModel.schedule.scheduleType, "Timer")
        self.assertEqual(settingsModel.schedule.timerMinutes, 15)
        timerFromTime = \
            datetime.time(datetime.strptime("00:00:00", "%H:%M:%S"))
        self.assertEqual(settingsModel.schedule.timerFromTime, timerFromTime)
        timerToTime = \
            datetime.time(datetime.strptime("23:59:00", "%H:%M:%S"))
        self.assertEqual(settingsModel.schedule.timerToTime, timerToTime)
        ValidateSettings(settingsModel)

    def test_read_weekly_cfg(self):
        """
        Test ability to read Weekly schedule settings from MyData.cfg
        """
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataWeekly.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        self.assertEqual(settingsModel.schedule.scheduleType, "Weekly")
        self.assertEqual(settingsModel.schedule.mondayChecked, True)
        self.assertEqual(settingsModel.schedule.tuesdayChecked, False)
        ValidateSettings(settingsModel)

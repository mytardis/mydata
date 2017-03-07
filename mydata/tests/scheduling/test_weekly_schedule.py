"""
Test Weekly schedule type.
"""
from datetime import datetime
from datetime import timedelta
import os

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


class WeeklyScheduleTester(MyDataSettingsTester):
    """
    Test Weekly schedule type.
    """
    def __init__(self, *args, **kwargs):
        super(WeeklyScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        """
        Don't have MyDataTester.setUp create a wx.App() instance .
        We'll create a MyData app instance instead.
        """
        super(WeeklyScheduleTester, self).setUp()
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        SETTINGS.Update(
            SettingsModel(configPath=configPath, checkForUpdates=False))
        SETTINGS.configPath = self.tempFilePath
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        SETTINGS.general.dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        SETTINGS.schedule.scheduleType = "Weekly"
        SETTINGS.schedule.mondayChecked = True
        SETTINGS.schedule.tuesdayChecked = True
        SETTINGS.schedule.wednesdayChecked = True
        SETTINGS.schedule.thursdayChecked = False
        SETTINGS.schedule.fridayChecked = True
        SETTINGS.schedule.saturdayChecked = True
        SETTINGS.schedule.sundayChecked = True
        SETTINGS.schedule.scheduledTime = \
            datetime.time(datetime.now().replace(microsecond=0) +
                          timedelta(minutes=1))
        SaveSettingsToDisk()

    def test_weekly_schedule(self):
        """
        Test Weekly schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 7)
        # TO DO: A way of testing that additional tasks are scheduled,
        # according to the timer interval.
        self.assertEqual(self.mydataApp.tasksModel.GetRowCount(), 1)
        self.assertEqual(self.mydataApp.tasksModel.GetValueByRow(0, 4), "Weekly (MTW-FSS)")
        self.mydataApp.tasksModel.DeleteAllRows()
        self.assertEqual(self.mydataApp.tasksModel.GetRowCount(), 0)
        self.assertIn(
            "CreateWeeklyTask - MainThread - DEBUG - Schedule type is Weekly",
            logger.loggerOutput.getvalue())

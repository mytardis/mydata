"""
Test Weekly schedule type.
"""
from datetime import datetime
from datetime import timedelta
import os

from .. import MyDataSettingsTester
from ...MyData import MyData
from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings


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
        self.settingsModel = SettingsModel(configPath=configPath, checkForUpdates=False)
        self.settingsModel.configPath = self.tempFilePath
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        self.settingsModel.general.dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.settingsModel.schedule.scheduleType = "Weekly"
        self.settingsModel.schedule.mondayChecked = True
        self.settingsModel.schedule.tuesdayChecked = True
        self.settingsModel.schedule.wednesdayChecked = True
        self.settingsModel.schedule.thursdayChecked = False
        self.settingsModel.schedule.fridayChecked = True
        self.settingsModel.schedule.saturdayChecked = True
        self.settingsModel.schedule.sundayChecked = True
        self.settingsModel.schedule.scheduledTime = \
            datetime.time(datetime.now().replace(microsecond=0) +
                          timedelta(minutes=1))
        SaveSettingsToDisk(self.settingsModel)

    def test_weekly_schedule(self):
        """
        Test Weekly schedule type.
        """
        ValidateSettings(self.settingsModel)
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'],
                                settingsModel=self.settingsModel)
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

    def tearDown(self):
        super(WeeklyScheduleTester, self).tearDown()
        self.mydataApp.GetMainFrame().Hide()
        self.mydataApp.GetMainFrame().Destroy()

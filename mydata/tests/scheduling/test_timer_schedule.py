"""
Test Timer schedule type.
"""
from datetime import datetime
import os

from .. import MyDataSettingsTester
from ...MyData import MyData
from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings


class TimerScheduleTester(MyDataSettingsTester):
    """
    Test Timer schedule type.
    """
    def __init__(self, *args, **kwargs):
        super(TimerScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(TimerScheduleTester, self).setUp()
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = SettingsModel(configPath=configPath,
                                           checkForUpdates=False)
        self.settingsModel.configPath = self.tempFilePath
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        self.settingsModel.general.dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.settingsModel.schedule.scheduleType = "Timer"
        self.settingsModel.schedule.timerMinutes = 15
        self.settingsModel.schedule.timerFromTime = \
            datetime.time(datetime.strptime("12:00 AM", "%I:%M %p"))
        self.settingsModel.schedule.timerToTime = \
            datetime.time(datetime.strptime("11:59 PM", "%I:%M %p"))
        SaveSettingsToDisk(self.settingsModel)

    def test_timer_schedule(self):
        """
        Test Timer schedule type.
        """
        ValidateSettings(self.settingsModel)
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'],
                                settingsModel=self.settingsModel)
        self.mydataApp.taskBarIcon.CreatePopupMenu()
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 7)
        # TO DO: A way of testing that additional tasks are scheduled,
        # according to the timer interval.

    def tearDown(self):
        super(TimerScheduleTester, self).tearDown()
        self.mydataApp.GetMainFrame().Hide()
        self.mydataApp.GetMainFrame().Destroy()

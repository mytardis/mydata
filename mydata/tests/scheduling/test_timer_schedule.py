"""
Test Timer schedule type.
"""
from datetime import datetime
import os

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


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
        SETTINGS.Update(
            SettingsModel(configPath=configPath, checkForUpdates=False))
        SETTINGS.configPath = self.tempFilePath
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        SETTINGS.general.dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        SETTINGS.schedule.scheduleType = "Timer"
        SETTINGS.schedule.timerMinutes = 15
        SETTINGS.schedule.timerFromTime = \
            datetime.time(datetime.strptime("12:00 AM", "%I:%M %p"))
        SETTINGS.schedule.timerToTime = \
            datetime.time(datetime.strptime("11:59 PM", "%I:%M %p"))
        SaveSettingsToDisk()

    def test_timer_schedule(self):
        """
        Test Timer schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        self.mydataApp.taskBarIcon.CreatePopupMenu()
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 7)
        self.assertIn(
            "CreateTimerTask - MainThread - DEBUG - Schedule type is Timer",
            logger.loggerOutput.getvalue())
        # TO DO: A way of testing that additional tasks are scheduled,
        # according to the timer interval.

    def tearDown(self):
        super(TimerScheduleTester, self).tearDown()
        self.mydataApp.GetMainFrame().Hide()
        self.mydataApp.GetMainFrame().Destroy()

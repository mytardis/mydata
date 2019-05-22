"""
Test Timer schedule type.
"""
import unittest
from datetime import datetime

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


@unittest.skip("Needs rewriting since MainLoop() has been added to tearDown")
class TimerScheduleTester(MyDataSettingsTester):
    """
    Test Timer schedule type.
    """
    def __init__(self, *args, **kwargs):
        super(TimerScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(TimerScheduleTester, self).setUp()
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        SETTINGS.schedule.scheduleType = "Timer"
        SETTINGS.schedule.timerMinutes = 15
        SETTINGS.schedule.timerFromTime = \
            datetime.time(datetime.strptime("12:00 AM", "%I:%M %p"))
        SETTINGS.schedule.timerToTime = \
            datetime.time(datetime.strptime("11:59 PM", "%I:%M %p"))

    def test_timer_schedule(self):
        """Test Timer schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        self.mydataApp.frame.taskBarIcon.CreatePopupMenu()
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        uploadsModel = DATAVIEW_MODELS['uploads']
        self.assertEqual(uploadsModel.GetCompletedCount(), 8)
        self.assertIn(
            "CreateTimerTask - MainThread - DEBUG - Schedule type is Timer",
            logger.loggerOutput.getvalue())
        # TO DO: A way of testing that additional tasks are scheduled,
        # according to the timer interval.

"""
Test Once schedule type with invalid date/time.
"""
from datetime import datetime
from datetime import timedelta

from ...settings import SETTINGS
from ...MyData import MyData
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import InvalidSettings
from .. import MyDataSettingsTester


class OnceScheduleTester(MyDataSettingsTester):
    """
    Test Once schedule type with invalid date/time.
    """
    def __init__(self, *args, **kwargs):
        super(OnceScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(OnceScheduleTester, self).setUp()
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        SETTINGS.schedule.scheduleType = "Once"
        SETTINGS.schedule.scheduledDate = datetime.date(datetime.now())
        SETTINGS.schedule.scheduledTime = \
            datetime.time(datetime.now().replace(microsecond=0) -
                          timedelta(minutes=1))
        SaveSettingsToDisk()

    def test_once_schedule(self):
        """
        Test Once schedule type with invalid date/time.
        """
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "scheduled_time")
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 0)
        # TO DO: A way of testing that additional tasks are scheduled,
        # according to the timer interval.

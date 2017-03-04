"""
Test Once schedule type.
"""
from datetime import datetime
from datetime import timedelta
import os

from ...settings import SETTINGS
from ...MyData import MyData
from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


class OnceScheduleTester(MyDataSettingsTester):
    """
    Test Once schedule type.
    """
    def __init__(self, *args, **kwargs):
        super(OnceScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(OnceScheduleTester, self).setUp()
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        SETTINGS.Update(
            SettingsModel(configPath=configPath, checkForUpdates=False))
        SETTINGS.configPath = self.tempFilePath
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SETTINGS.schedule.scheduleType = "Once"
        SETTINGS.schedule.scheduledDate = datetime.date(datetime.now())
        SETTINGS.schedule.scheduledTime = \
            datetime.time(datetime.now().replace(microsecond=0) +
                          timedelta(minutes=1))
        SaveSettingsToDisk()

    def test_once_schedule(self):
        """
        Test Once schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 7)
        # TO DO: A way of testing that additional tasks are scheduled,
        # according to the timer interval.

    def tearDown(self):
        super(OnceScheduleTester, self).tearDown()
        self.mydataApp.GetMainFrame().Hide()
        self.mydataApp.GetMainFrame().Destroy()

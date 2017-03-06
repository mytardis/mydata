"""
Test On Startup schedule type.
"""
import os

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


class OnStartupScheduleTester(MyDataSettingsTester):
    """
    Test On Startup schedule type.
    """
    def __init__(self, *args, **kwargs):
        super(OnStartupScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(OnStartupScheduleTester, self).setUp()
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
        SETTINGS.schedule.scheduleType = "On Startup"
        SaveSettingsToDisk()

    def test_on_startup_schedule(self):
        """
        Test On Startup schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 7)
        self.assertIn(
            "CreateOnStartupTask - MainThread - DEBUG - Schedule type is On Startup",
            logger.loggerOutput.getvalue())

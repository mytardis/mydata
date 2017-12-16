"""
Test On Startup schedule type.
"""
from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...dataviewmodels.dataview import DATAVIEW_MODELS
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
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        SETTINGS.schedule.scheduleType = "On Startup"
        SaveSettingsToDisk()

    def tearDown(self):
        super(OnStartupScheduleTester, self).tearDown()
        self.mydataApp.frame.Hide()
        self.mydataApp.frame.Destroy()

    def test_on_startup_schedule(self):
        """
        Test On Startup schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        uploadsModel = DATAVIEW_MODELS['uploads']
        self.assertEqual(uploadsModel.GetCompletedCount(), 8)
        self.assertIn(
            "CreateOnStartupTask - MainThread - DEBUG - Schedule type is On Startup",
            logger.loggerOutput.getvalue())

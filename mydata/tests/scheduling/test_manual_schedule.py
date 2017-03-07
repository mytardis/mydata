"""
Test Manual schedule type.
"""
import os

import wx

from ...settings import SETTINGS
from ...logs import logger
from ...MyData import MyData
from ...models.settings import SettingsModel
from ...models.settings import LastSettingsUpdateTrigger
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


class ManualScheduleTester(MyDataSettingsTester):
    """
    Test Manual schedule type.
    """
    def __init__(self, *args, **kwargs):
        super(ManualScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(ManualScheduleTester, self).setUp()
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
        SETTINGS.schedule.scheduleType = "Manually"
        SaveSettingsToDisk()

    def test_manual_schedule(self):
        """
        Test Manual schedule type.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        # If schedule type is "Manually", it will only run in response to a
        # User Interface response, so we'll set
        # SETTINGS.lastSettingsUpdateTrigger to simulate a UI trigger:
        SETTINGS.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.UI_RESPONSE
        # Having set SETTINGS.lastSettingsUpdateTrigger to
        # LastSettingsUpdateTrigger.UI_RESPONSE, MyData's settings validation
        # will assume that the settings came from MyData's interactive settings
        # dialog, so it will check whether MyData is set to start
        # automatically, but we can do this to save time:
        SETTINGS.lastCheckedAutostartValue = \
            SETTINGS.advanced.startAutomaticallyOnLogin
        pyEvent = wx.PyEvent()
        self.mydataApp.scheduleController.ApplySchedule(pyEvent,
                                                        runManually=True)
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 7)
        self.assertIn(
            "ApplySchedule - MainThread - DEBUG - Schedule type is Manually",
            logger.loggerOutput.getvalue())

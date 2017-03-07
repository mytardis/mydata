"""
Test ability to update settings from server.
"""
import os

from ...settings import SETTINGS
from ...models.settings import SettingsModel
from ...models.settings.serialize import LoadSettings
from ...models.settings.serialize import SaveSettingsToDisk
from .. import MyDataSettingsTester


class UpdatedSettingsTester(MyDataSettingsTester):
    """
    Test ability to update settings from server.
    """
    def setUp(self):
        """
        Set up for test.
        """
        super(UpdatedSettingsTester, self).setUp()
        configPath = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg"))
        self.assertTrue(os.path.exists(configPath))
        SETTINGS.Update(SettingsModel(configPath=configPath,
                                      checkForUpdates=False))
        SETTINGS.configPath = self.tempFilePath
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset"))
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SaveSettingsToDisk()

    def test_update_settings_from_server(self):
        """
        Test ability to update settings from server.

        For the purpose of testing, the updated values are hard-coded in
        mydata/tests/fake_mytardis_server.py
        """
        LoadSettings(SETTINGS, checkForUpdates=True)
        self.assertEqual(SETTINGS.general.contactName, "Someone Else")
        self.assertFalse(SETTINGS.advanced.validateFolderStructure)
        self.assertEqual(SETTINGS.miscellaneous.maxVerificationThreads, 2)
        self.assertEqual(str(SETTINGS.schedule.scheduledDate), "2020-01-01")
        self.assertEqual(str(SETTINGS.schedule.scheduledTime), "09:00:00")

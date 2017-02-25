"""
Test ability to update settings from server.
"""
import os

from .. import MyDataSettingsTester
from ...models.settings import SettingsModel
from ...models.settings.serialize import LoadSettings
from ...models.settings.serialize import SaveSettingsToDisk


class UpdatedSettingsTester(MyDataSettingsTester):
    """
    Test ability to update settings from server.
    """
    def setUp(self):
        """
        Set up for test.
        """
        super(UpdatedSettingsTester, self).setUp()
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = SettingsModel(configPath=configPath,
                                           checkForUpdates=False)
        self.settingsModel.configPath = self.tempFilePath
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        self.settingsModel.general.dataDirectory = dataDirectory
        SaveSettingsToDisk(self.settingsModel)

    def test_update_settings_from_server(self):
        """
        Test ability to update settings from server.

        For the purpose of testing, the updated values are hard-coded in
        mydata/tests/fake_mytardis_server.py
        """
        LoadSettings(self.settingsModel, checkForUpdates=True)
        self.assertEqual(self.settingsModel.general.contactName, "Someone Else")
        self.assertFalse(self.settingsModel.advanced.validateFolderStructure)
        self.assertEqual(self.settingsModel.miscellaneous.maxVerificationThreads, 2)
        self.assertEqual(str(self.settingsModel.schedule.scheduledDate),
                         "2020-01-01")
        self.assertEqual(str(self.settingsModel.schedule.scheduledTime),
                         "09:00:00")

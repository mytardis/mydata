"""
Test ability to update settings from server.
"""
from ...settings import SETTINGS
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
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        SaveSettingsToDisk()

    def test_update_settings_from_server(self):
        """Test ability to update settings from server.

        For the purpose of testing, the updated values are hard-coded in
        mydata/tests/fake_mytardis_server.py
        """
        LoadSettings(SETTINGS, checkForUpdates=True)
        self.assertEqual(SETTINGS.general.contactName, "Someone Else")
        self.assertFalse(SETTINGS.advanced.validateFolderStructure)
        self.assertEqual(SETTINGS.miscellaneous.maxVerificationThreads, 2)
        self.assertEqual(str(SETTINGS.schedule.scheduledDate), "2020-01-01")
        self.assertEqual(str(SETTINGS.schedule.scheduledTime), "09:00:00")

"""
Test ability to detect invalid email addresses in the Email / Dataset structure.
"""
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import InvalidSettings
from .. import MyDataTester


class ScanFoldersTester(MyDataTester):
    """
    Test ability to detect invalid email addresses in the Email / Dataset structure.
    """
    def setUp(self):
        super(ScanFoldersTester, self).setUp()
        super(ScanFoldersTester, self).InitializeAppAndFrame(
            'ScanFoldersTester')

    def test_scan_folders(self):
        """
        Test ability to detect invalid email addresses in the Email / Dataset structure.
        """
        self.UpdateSettingsFromCfg("testdataInvalidEmailDataset")
        with self.assertRaises(InvalidSettings):
            ValidateSettings()

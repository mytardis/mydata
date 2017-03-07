"""
Test ability to detect invalid email addresses in the Email / Dataset structure.
"""
import os

from ...settings import SETTINGS
from ...models.settings import SettingsModel
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
        pathToTestConfig = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataInvalidEmailDataset.cfg"))
        self.assertTrue(os.path.exists(pathToTestConfig))
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataInvalidEmailDataset"))
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        with self.assertRaises(InvalidSettings):
            ValidateSettings()

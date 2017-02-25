"""
Test ability to detect invalid email addresses in the Email / Dataset structure.
"""
import os

from .. import MyDataTester
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import InvalidSettings


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
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataInvalidEmailDataset.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataInvalidEmailDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        with self.assertRaises(InvalidSettings):
            ValidateSettings(settingsModel)

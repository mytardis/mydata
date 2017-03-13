"""
Test ability to scan folders with the Email / Dataset structure.
"""
from .. import MyDataScanFoldersTester


class ScanFoldersTester(MyDataScanFoldersTester):
    """
    Test ability to scan folders with the Email / Dataset structure.
    """
    def setUp(self):
        super(ScanFoldersTester, self).setUp()
        super(ScanFoldersTester, self).InitializeAppAndFrame(
            title='ScanFoldersTester')

    def test_scan_folders(self):
        """
        Test ability to scan folders with the Email / Dataset structure.
        """
        self.UpdateSettingsFromCfg("testdataEmailDataset")
        self.ScanFolders()
        self.AssertUsers(["testuser1", "testuser2"])
        self.AssertFolders(["Birds", "Flowers"])
        self.AssertNumFiles(5)

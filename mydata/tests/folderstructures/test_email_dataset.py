"""
Test ability to scan folders with the Email / Dataset structure.
"""
from .. import MyDataScanFoldersTester
from .. import ValidateSettingsAndScanFolders


class ScanFoldersTester(MyDataScanFoldersTester):
    """
    Test ability to scan folders with the Email / Dataset structure.
    """
    def test_scan_folders(self):
        """Test ability to scan folders with the Email / Dataset structure.
        """
        self.UpdateSettingsFromCfg("testdataEmailDataset")
        ValidateSettingsAndScanFolders()
        self.AssertUsers(["testuser1", "testuser2"])
        self.AssertFolders(["Birds", "Flowers"])
        self.AssertNumFiles(5)

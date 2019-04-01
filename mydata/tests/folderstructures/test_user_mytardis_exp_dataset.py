"""
Test ability to scan the Username / MyTardis / Experiment / Dataset folder
structure.
"""
from .. import MyDataScanFoldersTester
from .. import ValidateSettingsAndScanFolders


class ScanUserMyTardisExpDatasetTester(MyDataScanFoldersTester):
    """
    Test ability to scan the Username / MyTardis / Experiment / Dataset folder
    structure.
    """
    def test_scan_folders(self):
        """Test ability to scan the Username / MyTardis / Experiment / Dataset folder structure
        """
        self.UpdateSettingsFromCfg("testdataUserMyTardisExpDataset")
        ValidateSettingsAndScanFolders()
        self.AssertUsers(["testuser1", "testuser2", "testuser3"])
        self.AssertFolders(["Birds", "Flowers"])
        self.AssertNumFiles(5)

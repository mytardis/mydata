"""
Test ability to scan the Dataset folder structure.
"""
from .. import MyDataScanFoldersTester
from .. import ValidateSettingsAndScanFolders


class ScanDatasetTester(MyDataScanFoldersTester):
    """
    Test ability to scan the Dataset folder structure.
    """
    def test_scan_folders(self):
        """
        Test ability to scan the Dataset folder structure.
        """
        self.UpdateSettingsFromCfg("testdataDataset")
        ValidateSettingsAndScanFolders()
        self.AssertFolders(["Birds", "Flowers"])
        self.AssertNumFiles(5)

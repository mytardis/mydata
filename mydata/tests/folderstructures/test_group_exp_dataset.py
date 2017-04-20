"""
Test ability to scan the User Group / Experiment / Dataset folder structure.
"""
from .. import MyDataScanFoldersTester


class ScanGroupExpDatasetTester(MyDataScanFoldersTester):
    """
    Test ability to scan the User Group / Experiment / Dataset folder structure.
    """
    def setUp(self):
        super(ScanGroupExpDatasetTester, self).setUp()
        super(ScanGroupExpDatasetTester, self).InitializeAppAndFrame(
            'ScanGroupExpDatasetTester')

    def test_scan_folders(self):
        """
        Test ability to scan the User Group / Experiment / Dataset folder structure.
        """
        self.UpdateSettingsFromCfg("testdataGroupExpDataset")
        self.ValidateSettingsAndScanFolders()
        self.assertEqual(
            sorted(self.groupsModel.GetValuesForColname("Full Name")),
            ["TestFacility-Group1", "TestFacility-Group2"])
        self.AssertFolders(["Birds", "Flowers"])
        self.AssertNumFiles(5)

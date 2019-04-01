"""
Test ability to scan the User Group / Experiment / Dataset folder structure.
"""
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from .. import MyDataScanFoldersTester
from .. import ValidateSettingsAndScanFolders


class ScanGroupExpDatasetTester(MyDataScanFoldersTester):
    """
    Test ability to scan the User Group / Experiment / Dataset folder structure.
    """
    def test_scan_folders(self):
        """Test ability to scan the User Group / Experiment / Dataset folder structure
        """
        self.UpdateSettingsFromCfg("testdataGroupExpDataset")
        ValidateSettingsAndScanFolders()
        groupsModel = DATAVIEW_MODELS['groups']
        self.assertEqual(
            sorted(groupsModel.GetValuesForColname("Full Name")),
            ["TestFacility-Group1", "TestFacility-Group2"])
        self.AssertFolders(["Birds", "Flowers"])
        self.AssertNumFiles(5)

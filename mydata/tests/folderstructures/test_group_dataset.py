"""
Test ability to scan the User Group / Dataset folder structure.
"""
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from .. import MyDataScanFoldersTester
from .. import ValidateSettingsAndScanFolders


class ScanGroupDatasetTester(MyDataScanFoldersTester):
    """
    Test ability to scan the User Group / Dataset folder structure.
    """
    def test_scan_folders(self):
        """
        Test ability to scan the User Group / Dataset folder structure.
        """
        self.UpdateSettingsFromCfg("testdataGroupDataset")
        ValidateSettingsAndScanFolders()
        groupsModel = DATAVIEW_MODELS['groups']
        self.assertEqual(
            sorted(groupsModel.GetValuesForColname("Full Name")),
            ["TestFacility-Group1", "TestFacility-Group2"])
        self.AssertFolders(["Birds", "Flowers"])
        self.AssertNumFiles(5)

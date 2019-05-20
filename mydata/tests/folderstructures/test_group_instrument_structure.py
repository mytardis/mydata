"""
Test ability to scan the User Group / Instrument / Full Name / Dataset folder structure.
"""
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...models.settings.validation import CheckStructureAndCountDatasets
from .. import MyDataScanFoldersTester
from .. import ValidateSettingsAndScanFolders


class ScanUserGroupInstrumentTester(MyDataScanFoldersTester):
    """
    Test ability to scan the User Group / Instrument / Full Name / Dataset folder structure.
    """
    def test_scan_folders(self):
        """Test ability to scan the User Group / Instrument / Full Name / Dataset folder structure.
        """
        self.UpdateSettingsFromCfg("testdataGroupInstrument")
        datasetCount = CheckStructureAndCountDatasets()
        self.assertEqual(datasetCount, 8)
        ValidateSettingsAndScanFolders()
        groupsModel = DATAVIEW_MODELS['groups']
        self.assertEqual(
            sorted(groupsModel.GetValuesForColname("Full Name")),
            ["TestFacility-Group1", "TestFacility-Group2"])
        self.AssertFolders(
            ['Dataset 001', 'Dataset 002', 'Dataset 003', 'Dataset 004',
             'Dataset 005', 'Dataset 006', 'Dataset 007', 'Dataset 008'])
        self.AssertNumFiles(8)

"""
Test ability to scan the User Group / Instrument / Full Name / Dataset folder structure.
"""
from ...models.settings.validation import CheckStructureAndCountDatasets
from .. import MyDataScanFoldersTester


class ScanUserGroupInstrumentTester(MyDataScanFoldersTester):
    """
    Test ability to scan the User Group / Instrument / Full Name / Dataset folder structure.
    """
    def setUp(self):
        super(ScanUserGroupInstrumentTester, self).setUp()
        super(ScanUserGroupInstrumentTester, self).InitializeAppAndFrame(
            'ScanUserGroupInstrumentTester')

    def test_scan_folders(self):
        """
        Test ability to scan the User Group / Instrument / Full Name / Dataset folder structure.
        """
        self.UpdateSettingsFromCfg("testdataGroupInstrument")
        datasetCount = CheckStructureAndCountDatasets()
        self.assertEqual(datasetCount, 8)
        self.ScanFolders()
        self.assertEqual(
            sorted(self.groupsModel.GetValuesForColname("Full Name")),
            ["TestFacility-Group1", "TestFacility-Group2"])
        self.AssertFolders(
            ['Dataset 001', 'Dataset 002', 'Dataset 003', 'Dataset 004',
             'Dataset 005', 'Dataset 006', 'Dataset 007', 'Dataset 008'])
        self.AssertNumFiles(8)

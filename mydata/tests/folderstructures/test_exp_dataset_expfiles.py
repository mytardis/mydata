"""
Test ability to upload files at the Experiment level.
"""
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from .. import MyDataScanFoldersTester
from .. import ValidateSettingsAndScanFolders


class UploadExpFilesTester(MyDataScanFoldersTester):
    """
    Test ability to upload files at the Experiment level.
    """
    def setUp(self):
        super(UploadExpFilesTester, self).setUp()
        super(UploadExpFilesTester, self).InitializeAppAndFrame(
            'UploadExpFilesTester')

    def test_upload_exp_files(self):
        """
        Test ability to upload files at the Experiment level.
        """
        self.UpdateSettingsFromCfg("testdataExpDatasetExpFiles")
        ValidateSettingsAndScanFolders()

        folders = []
        foldersModel = DATAVIEW_MODELS['folders']
        for row in range(foldersModel.GetRowCount()):
            folders.append(foldersModel.GetFolderRecord(row).folderName)
        self.assertEqual(sorted(folders),
                         ["Birds", "Flowers",
                          "__EXPERIMENT_FILES__",
                          "__EXPERIMENT_FILES__"])

        totalNumFiles = 0
        foundExpFilename = False
        for row in range(foldersModel.GetRowCount()):
            folderModel = foldersModel.GetFolderRecord(row)
            numFiles = folderModel.GetNumFiles()
            totalNumFiles += numFiles
            for fileIndex in range(numFiles):
                if folderModel.GetDataFileName(fileIndex) == "exp_file1.txt":
                    foundExpFilename = True
        self.assertEqual(totalNumFiles, 7)
        self.assertTrue(foundExpFilename)

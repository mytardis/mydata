"""
Test folder model
"""
import os
import sys
import tempfile

import wx

from ...settings import SETTINGS
from ...models.folder import FolderModel
from ...models.user import UserModel
from .. import MyDataTester


class FolderModelTester(MyDataTester):
    """
    Test folder model
    """
    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(None, title='FolderModelTester')
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        with tempfile.NamedTemporaryFile() as tempFile:
            self.includesFilePath = tempFile.name
        with tempfile.NamedTemporaryFile() as tempFile:
            self.excludesFilePath = tempFile.name

    def test_folder_model(self):
        """Test folder model
        """
        testuser1 = UserModel(username="testuser1")
        dataViewId = 1
        folder = "Flowers"
        location = os.path.join(SETTINGS.general.dataDirectory, "testuser1")
        userFolderName = "testuser1"
        groupFolderName = None

        # Filenames:

        #  1. 1024px-Colourful_flowers.JPG
        #  2. Flowers_growing_on_the_campus_of_Cebu_City_National
        #     _Science_High_School.jpg
        #  3. Pond_Water_Hyacinth_Flowers.jpg
        #  4. existing_unverified_full_size_file.txt
        #  5. existing_unverified_incomplete_file.txt
        #  6. missing_mydata_replica_api_endpoint.txt
        #  7. existing_verified_file.txt
        #  8. zero_sized_file.txt

        # We want this test to run on Mac, Linux and Windows, but
        # Windows uses a case-insensitive filesystem, so the
        # expected results will be slightly different.

        with open(self.includesFilePath, 'w') as includesFile:
            includesFile.write("# Includes comment\n")
            includesFile.write("; Includes comment\n")
            includesFile.write("\n")
            includesFile.write("*.jpg\n")
            includesFile.write("zero*\n")

        with open(self.excludesFilePath, 'w') as excludesFile:
            excludesFile.write("# Excludes comment\n")
            excludesFile.write("; Excludes comment\n")
            excludesFile.write("\n")
            excludesFile.write(".DS_Store\n")
            excludesFile.write("*.bak\n")
            excludesFile.write("*.txt\n")
            excludesFile.write("*.JPG\n")

        SETTINGS.filters.includesFile = self.includesFilePath
        SETTINGS.filters.excludesFile = self.excludesFilePath
        self.assertTrue(FolderModel.MatchesIncludes("image.jpg"))
        self.assertTrue(FolderModel.MatchesExcludes("filename.bak"))

        SETTINGS.filters.useIncludesFile = False
        SETTINGS.filters.useExcludesFile = False
        folderModel = FolderModel(dataViewId, folder, location, userFolderName,
                                  groupFolderName, testuser1)
        self.assertEqual(folderModel.numFiles, 8)

        SETTINGS.filters.useIncludesFile = True
        SETTINGS.filters.useExcludesFile = True
        expectedFiles = [
            ('Flowers_growing_on_the_campus_of_Cebu_City_'
             'National_Science_High_School.jpg'),
            'Pond_Water_Hyacinth_Flowers.jpg',
            'zero_sized_file.txt']
        if sys.platform.startswith("win"):
            expectedFiles.insert(0, '1024px-Colourful_flowers.JPG')
        folderModel = FolderModel(dataViewId, folder, location, userFolderName,
                                  groupFolderName, testuser1)
        self.assertEqual(
            sorted([os.path.basename(f) for f in
                    folderModel.dataFilePaths['files']]),
            expectedFiles)

        SETTINGS.filters.useIncludesFile = True
        SETTINGS.filters.useExcludesFile = False
        folderModel = FolderModel(dataViewId, folder, location, userFolderName,
                                  groupFolderName, testuser1)
        self.assertEqual(
            sorted([os.path.basename(f) for f in
                    folderModel.dataFilePaths['files']]),
            expectedFiles)

        SETTINGS.filters.useIncludesFile = False
        SETTINGS.filters.useExcludesFile = True
        if sys.platform.startswith("win"):
            expectedFiles = []
        else:
            expectedFiles = [
                ('Flowers_growing_on_the_campus_of_Cebu_City_'
                 'National_Science_High_School.jpg'),
                'Pond_Water_Hyacinth_Flowers.jpg'
            ]
        folderModel = FolderModel(dataViewId, folder, location, userFolderName,
                                  groupFolderName, testuser1)
        self.assertEqual(
            sorted([os.path.basename(f) for f in
                    folderModel.dataFilePaths['files']]),
            expectedFiles)

    def tearDown(self):
        if os.path.exists(self.includesFilePath):
            os.remove(self.includesFilePath)
        if os.path.exists(self.excludesFilePath):
            os.remove(self.excludesFilePath)
        self.frame.Hide()
        self.frame.Destroy()

"""
Test folder model
"""
import unittest
import os
import tempfile

import wx

from mydata.models.folder import FolderModel
from mydata.models.user import UserModel

from mydata.models.settings import SettingsModel


class FolderModelTester(unittest.TestCase):
    """
    Test folder model
    """
    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(None, title='FolderModelTester')
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = SettingsModel(configPath=configPath,
                                           checkForUpdates=False)
        self.settingsModel.SetDataDirectory(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "../testdata", "testdataUsernameDataset"))
        with tempfile.NamedTemporaryFile() as tempFile:
            self.includesFilePath = tempFile.name
        with tempfile.NamedTemporaryFile() as tempFile:
            self.excludesFilePath = tempFile.name

    def test_folder_model(self):
        """
        Test folder model
        """
        testuser1 = UserModel(username="testuser1")
        dataViewId = 1
        folder = "Flowers"
        location = os.path.join(self.settingsModel.GetDataDirectory(),
                                "testuser1")
        userFolderName = "testuser1"
        groupFolderName = None

        with open(self.includesFilePath, 'w') as includesFile:
            includesFile.write("# Includes comment\n")
            includesFile.write("; Includes comment\n")
            includesFile.write("*.txt\n")
            includesFile.write("*.jpg\n")

        with open(self.excludesFilePath, 'w') as excludesFile:
            excludesFile.write("# Includes comment\n")
            excludesFile.write("; Includes comment\n")
            excludesFile.write(".DS_Store\n")
            excludesFile.write("*.bak\n")

        self.settingsModel.SetIncludesFile(self.includesFilePath)
        self.settingsModel.SetExcludesFile(self.excludesFilePath)
        folderModel = \
            FolderModel(dataViewId, folder, location,
                        userFolderName, groupFolderName, testuser1,
                        self.settingsModel)

        self.assertTrue(folderModel.MatchesIncludes("image.jpg"))
        self.assertTrue(folderModel.MatchesExcludes("filename.bak"))

    def tearDown(self):
        if os.path.exists(self.includesFilePath):
            os.remove(self.includesFilePath)
        if os.path.exists(self.excludesFilePath):
            os.remove(self.excludesFilePath)
        self.frame.Hide()
        self.frame.Destroy()

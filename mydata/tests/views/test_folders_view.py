"""
Test ability to open folders view.
"""
import os

from ...models.folder import FolderModel
from ...models.user import UserModel
from ...dataviewmodels.folders import FoldersModel
from ...views.folders import FoldersView

from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from .. import MyDataSettingsTester


class FoldersViewTester(MyDataSettingsTester):
    """
    Test ability to open folders view.
    """
    def setUp(self):
        super(FoldersViewTester, self).setUp()
        super(FoldersViewTester, self).InitializeAppAndFrame(
            'FoldersViewTester')
        self.usersModel = None
        self.groupsModel = None
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = SettingsModel(configPath=configPath,
                                           checkForUpdates=False)
        self.settingsModel.configPath = self.tempFilePath
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        self.settingsModel.general.dataDirectory = \
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "../testdata", "testdataUsernameDataset")
        SaveSettingsToDisk(self.settingsModel)
        self.foldersModel = FoldersModel(self.usersModel, self.groupsModel,
                                         self.settingsModel)
        self.foldersView = FoldersView(self.frame, foldersModel=self.foldersModel)

    def test_folders_view(self):
        """
        Test ability to open folders view.
        """
        testuser1 = UserModel.GetUserByUsername(self.settingsModel, "testuser1")
        dataViewId = 1
        folder = "Flowers"
        location = "/path/to/testuser1/"
        userFolderName = "testuser1"
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, folder, location,
                        userFolderName, groupFolderName, testuser1,
                        self.settingsModel)
        self.foldersModel.AddRow(folderModel)
        self.assertEqual(self.foldersModel.GetValueByRow(0, 1), "Flowers")
        self.assertEqual(self.foldersModel.GetRowCount(), 1)
        self.assertEqual(self.foldersModel.GetUnfilteredRowCount(), 1)
        self.assertEqual(self.foldersModel.GetFilteredRowCount(), 0)
        folder = "Birds"
        folderModel = \
            FolderModel(dataViewId, folder, location,
                        userFolderName, groupFolderName, testuser1,
                        self.settingsModel)
        self.foldersModel.AddRow(folderModel)
        self.assertEqual(self.foldersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.foldersModel.GetFilteredRowCount(), 0)
        self.foldersModel.Filter("Flowers")
        self.assertEqual(self.foldersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.foldersModel.GetFilteredRowCount(), 1)
        self.foldersModel.Filter("")
        self.assertEqual(self.foldersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.foldersModel.GetFilteredRowCount(), 0)
        self.foldersModel.DeleteAllRows()
        self.assertEqual(self.foldersModel.GetUnfilteredRowCount(), 0)
        self.assertEqual(self.foldersModel.GetFilteredRowCount(), 0)

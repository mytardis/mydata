"""
Test ability to open folders view.
"""
import unittest

import six

from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...models.folder import FolderModel
from ...models.user import UserModel
from ...views.dataview import MyDataDataView
from .. import MyDataSettingsTester


@unittest.skipIf(six.PY3, "Not working in Python 3 yet")
class FoldersViewTester(MyDataSettingsTester):
    """
    Test ability to open folders view.
    """
    def setUp(self):
        super(FoldersViewTester, self).setUp()
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")

    def test_folders_view(self):
        """Test ability to open folders view
        """
        foldersModel = DATAVIEW_MODELS['folders']
        # Create folders view:
        dataView = MyDataDataView(self.app.frame, 'folders')
        testuser1 = UserModel.GetUserByUsername("testuser1")
        dataViewId = 1
        folder = "Flowers"
        location = "/path/to/testuser1/"
        userFolderName = "testuser1"
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, folder, location,
                        userFolderName, groupFolderName, testuser1)
        foldersModel.AddRow(folderModel)
        self.assertEqual(foldersModel.GetValueByRow(0, 1), "Flowers")
        self.assertEqual(foldersModel.GetRowCount(), 1)
        self.assertEqual(foldersModel.GetUnfilteredRowCount(), 1)
        self.assertEqual(foldersModel.GetFilteredRowCount(), 0)
        folder = "Birds"
        folderModel = \
            FolderModel(dataViewId, folder, location,
                        userFolderName, groupFolderName, testuser1)
        foldersModel.AddRow(folderModel)
        self.assertEqual(foldersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(foldersModel.GetFilteredRowCount(), 0)
        foldersModel.Filter("Flowers")
        self.assertEqual(foldersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(foldersModel.GetFilteredRowCount(), 1)
        foldersModel.Filter("")
        self.assertEqual(foldersModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(foldersModel.GetFilteredRowCount(), 0)
        foldersModel.DeleteAllRows()
        self.assertEqual(foldersModel.GetUnfilteredRowCount(), 0)
        self.assertEqual(foldersModel.GetFilteredRowCount(), 0)
        dataView.Destroy()

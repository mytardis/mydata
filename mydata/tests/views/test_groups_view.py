"""
Test ability to open groups view.
"""
import unittest

import wx

from ...dataviewmodels.groups import GroupsModel
from ...models.group import GroupModel
from ...views.groups import GroupsView


class GroupsViewTester(unittest.TestCase):
    """
    Test ability to open groups view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='GroupsViewTester')
        self.settingsModel = None
        self.groupsModel = GroupsModel(self.settingsModel)
        self.groupsView = GroupsView(self.frame, groupsModel=self.groupsModel)
        self.frame.Show()

    def test_groups_view(self):
        """
        Test ability to open groups view.
        """
        # pylint: disable=no-self-use

        dataViewId = self.groupsModel.GetMaxDataViewId() + 1
        testgroup1 = GroupModel(name="Test Group 1")
        testgroup1.dataViewId = dataViewId
        self.groupsModel.AddRow(testgroup1)
        dataViewId = self.groupsModel.GetMaxDataViewId() + 1
        testgroup2 = GroupModel(name="Test Group 2")
        testgroup2.dataViewId = dataViewId
        self.groupsModel.AddRow(testgroup2)

        self.groupsModel.Compare(testgroup1, testgroup2, col=1, ascending=True)

        self.assertEqual(self.groupsModel.GetValueByRow(0, 1), "Test Group 1")
        self.assertEqual(self.groupsModel.GetValueByRow(1, 1), "Test Group 2")
        self.assertEqual(self.groupsModel.GetRowCount(), 2)
        self.assertEqual(self.groupsModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.groupsModel.GetFilteredRowCount(), 0)
        self.groupsModel.Filter("Test Group 2")
        self.assertEqual(self.groupsModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.groupsModel.GetFilteredRowCount(), 1)
        self.groupsModel.Filter("notfound")
        self.assertEqual(self.groupsModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.groupsModel.GetFilteredRowCount(), 2)
        self.groupsModel.Filter("")
        self.assertEqual(self.groupsModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(self.groupsModel.GetFilteredRowCount(), 0)
        self.groupsModel.DeleteAllRows()
        self.assertEqual(self.groupsModel.GetUnfilteredRowCount(), 0)
        self.assertEqual(self.groupsModel.GetFilteredRowCount(), 0)

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()

"""
Test ability to open groups view.
"""
import unittest

import six
import wx

from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...dataviewmodels.groups import GroupsModel
from ...models.group import GroupModel
from ...settings import SETTINGS
from ...views.dataview import MyDataDataView


@unittest.skipIf(six.PY3, "Not working in Python 3 yet")
class GroupsViewTester(unittest.TestCase):
    """
    Test ability to open groups view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)
        self.app.SetAppName('GroupsViewTester')
        self.frame = wx.Frame(None, title='GroupsViewTester')
        DATAVIEW_MODELS['groups'] = GroupsModel()
        self.groupsView = MyDataDataView(self.frame, 'groups')
        self.frame.Show()

    def test_groups_view(self):
        """
        Test ability to open groups view.
        """
        groupsModel = DATAVIEW_MODELS['groups']
        SETTINGS.advanced.groupPrefix = ""
        dataViewId = groupsModel.GetMaxDataViewId() + 1
        testgroup1 = GroupModel(name="Test Group 1")
        testgroup1.dataViewId = dataViewId
        groupsModel.AddRow(testgroup1)
        dataViewId = groupsModel.GetMaxDataViewId() + 1
        testgroup2 = GroupModel(name="Test Group 2")
        testgroup2.dataViewId = dataViewId
        groupsModel.AddRow(testgroup2)

        groupsModel.Compare(testgroup1, testgroup2, col=1, ascending=True)

        self.assertEqual(groupsModel.GetValueByRow(0, 1), "Test Group 1")
        self.assertEqual(groupsModel.GetValueByRow(1, 1), "Test Group 2")
        self.assertEqual(groupsModel.GetRowCount(), 2)
        self.assertEqual(groupsModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(groupsModel.GetFilteredRowCount(), 0)
        groupsModel.Filter("Test Group 2")
        self.assertEqual(groupsModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(groupsModel.GetFilteredRowCount(), 1)
        groupsModel.Filter("notfound")
        self.assertEqual(groupsModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(groupsModel.GetFilteredRowCount(), 2)
        groupsModel.Filter("")
        self.assertEqual(groupsModel.GetUnfilteredRowCount(), 2)
        self.assertEqual(groupsModel.GetFilteredRowCount(), 0)
        groupsModel.DeleteAllRows()
        self.assertEqual(groupsModel.GetUnfilteredRowCount(), 0)
        self.assertEqual(groupsModel.GetFilteredRowCount(), 0)

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()

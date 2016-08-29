"""
Test ability to open groups view.
"""
import unittest
import wx

from mydata.dataviewmodels.groups import GroupsModel
from mydata.views.groups import GroupsView


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
        pass

    def tearDown(self):
        self.frame.Destroy()

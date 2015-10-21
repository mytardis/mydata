"""
Test ability to open groups view.
"""
import unittest
import logging
import wx

from mydata.dataviewmodels.groups import GroupsModel
from mydata.views.groups import GroupsView

logger = logging.getLogger(__name__)


class GroupsViewTester(unittest.TestCase):
    """
    Test ability to open groups view.
    """
    def test_groups_view(self):
        """
        Test ability to open groups view.
        """
        # pylint: disable=no-self-use

        app = wx.App(redirect=False)  # pylint: disable=unused-variable
        frame = wx.Frame(None)
        settingsModel = None
        groupsModel = GroupsModel(settingsModel)
        GroupsView(frame, groupsModel=groupsModel)
        frame.Show()
        frame.Destroy()

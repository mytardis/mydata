"""
Test ability to open folders view.
"""
import unittest
import logging
import wx

from mydata.dataviewmodels.folders import FoldersModel
from mydata.views.folders import FoldersView

logger = logging.getLogger(__name__)


class FoldersViewTester(unittest.TestCase):
    """
    Test ability to open folders view.
    """
    def test_folders_view(self):
        """
        Test ability to open folders view.
        """
        # pylint: disable=no-self-use

        app = wx.App(redirect=False)  # pylint: disable=unused-variable
        frame = wx.Frame(None)
        usersModel = None
        groupsModel = None
        settingsModel = None
        foldersModel = FoldersModel(usersModel, groupsModel, settingsModel)
        FoldersView(frame, foldersModel=foldersModel)
        frame.Show()
        frame.Destroy()

"""
Test ability to open folders view.
"""
import unittest
import wx

from mydata.dataviewmodels.folders import FoldersModel
from mydata.views.folders import FoldersView


class FoldersViewTester(unittest.TestCase):
    """
    Test ability to open folders view.
    """

    def setUp(self):
        self.app = wx.App(redirect=False)
        self.frame = wx.Frame(None, title='FoldersViewTester')
        self.usersModel = None
        self.groupsModel = None
        self.settingsModel = None
        self.foldersModel = FoldersModel(self.usersModel, self.groupsModel, self.settingsModel)
        self.foldersView = FoldersView(self.frame, foldersModel=self.foldersModel)
        self.frame.Show()

    def test_folders_view(self):
        """
        Test ability to open folders view.
        """
        # pylint: disable=no-self-use
        pass

    def tearDown(self):
        self.frame.Destroy()

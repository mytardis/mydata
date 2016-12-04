"""
Test ability to open users view.
"""
import unittest
import wx

from mydata.dataviewmodels.users import UsersModel
from mydata.views.users import UsersView


class UsersViewTester(unittest.TestCase):
    """
    Test ability to open users view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='UsersViewTester')
        self.settingsModel = None
        self.usersModel = UsersModel(self.settingsModel)
        self.usersView = UsersView(self.frame, usersModel=self.usersModel)
        self.frame.Show()

    def test_users_view(self):
        """
        Test ability to open users view.
        """
        # pylint: disable=no-self-use
        pass

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()

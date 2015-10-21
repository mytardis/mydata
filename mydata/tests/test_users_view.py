"""
Test ability to open users view.
"""
import unittest
import logging
import wx

from mydata.dataviewmodels.users import UsersModel
from mydata.views.users import UsersView

logger = logging.getLogger(__name__)


class UsersViewTester(unittest.TestCase):
    """
    Test ability to open users view.
    """
    def test_users_view(self):
        """
        Test ability to open users view.
        """
        # pylint: disable=no-self-use

        app = wx.App(redirect=False)  # pylint: disable=unused-variable
        frame = wx.Frame(None)
        settingsModel = None
        usersModel = UsersModel(settingsModel)
        UsersView(frame, usersModel=usersModel)
        frame.Show()
        frame.Destroy()

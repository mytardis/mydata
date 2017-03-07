"""
Test ability to open verifications view.
"""
import unittest
import wx

from ...dataviewmodels.verifications import VerificationsModel
from ...views.dataview import MyDataDataView


class VerificationsViewTester(unittest.TestCase):
    """
    Test ability to open verifications view.
    """

    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='VerificationsViewTester')
        self.frame.Show()

    def test_verifications_view(self):
        """
        Test ability to open verifications view.
        """
        verificationsModel = VerificationsModel()
        MyDataDataView(self.frame, verificationsModel)

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()

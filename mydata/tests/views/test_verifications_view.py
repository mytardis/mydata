"""
Test ability to open verifications view.
"""
import unittest
import wx

from ...dataviewmodels.verifications import VerificationsModel
from ...views.verifications import VerificationsView


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
        VerificationsView(self.frame, verificationsModel=verificationsModel)

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()

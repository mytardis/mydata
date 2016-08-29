"""
Test ability to open verifications view.
"""
import unittest
import wx

from mydata.dataviewmodels.verifications import VerificationsModel
from mydata.views.verifications import VerificationsView


class VerificationsViewTester(unittest.TestCase):
    """
    Test ability to open verifications view.
    """

    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='VerificationsViewTester')
        self.verificationsModel = VerificationsModel()
        VerificationsView(self.frame, verificationsModel=self.verificationsModel)
        self.frame.Show()

    def test_verifications_view(self):
        """
        Test ability to open verifications view.
        """
        # pylint: disable=no-self-use
        pass

    def tearDown(self):
        self.frame.Destroy()

"""
Test ability to open connectivity view.
"""
import unittest
import wx

from mydata.utils.exceptions import NoActiveNetworkInterface
from mydata.views.connectivity import ReportNoActiveInterfaces


class LogViewTester(unittest.TestCase):
    """
    Test ability to open connectivity view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='LogViewTester')
        self.frame.Show()

    def test_log_view(self):
        """
        Test ability to open connectivity view.
        """
        with self.assertRaises(NoActiveNetworkInterface):
            ReportNoActiveInterfaces()

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()

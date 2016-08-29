"""
Test ability to open log view.
"""
import unittest
import wx

from mydata.views.log import LogView


class LogViewTester(unittest.TestCase):
    """
    Test ability to open log view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='LogViewTester')
        self.settingsModel = None
        self.logView = LogView(self.frame, self.settingsModel)
        self.frame.Show()

    def test_log_view(self):
        """
        Test ability to open log view.
        """
        # pylint: disable=no-self-use
        pass

    def tearDown(self):
        self.frame.Destroy()

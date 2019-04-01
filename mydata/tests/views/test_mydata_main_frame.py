"""
Test ability to display MyData's main frame.
"""
import unittest

import six
import wx

from ...views.mydata import MyDataFrame


@unittest.skipIf(six.PY3, "Not working in Python 3 yet")
class MyDataMainFrameTester(unittest.TestCase):
    """Test ability to display MyData's main frame
    """
    def setUp(self):
        self.app = wx.App()
        self.mydataFrame = MyDataFrame()

    def tearDown(self):
        self.mydataFrame.Hide()
        self.mydataFrame.Destroy()

    def test_mydata_main_frame(self):
        """
        Test ability to display MyData's main frame.
        """
        self.mydataFrame.Show()

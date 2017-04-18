"""
Test ability to display MyData's main frame.
"""
import unittest
import wx

from ...MyData import MyDataFrame


class MyDataMainFrameTester(unittest.TestCase):
    """
    Test ability to display MyData's main frame.
    """
    def setUp(self):
        self.app = wx.App()
        self.mydataFrame = MyDataFrame(title="MyData", dataViewModels=None)

    def tearDown(self):
        self.mydataFrame.Hide()
        self.mydataFrame.Destroy()

    def test_mydata_main_frame(self):
        """
        Test ability to display MyData's main frame.
        """
        self.mydataFrame.Show()

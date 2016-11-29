"""
Test ability to display MyData's main frame.

The enhanced status bar functionality (for displaying a connected
or disconnected icon in the status bar) should probably be removed,
but while it still exists in the code, we should test it.
"""
import unittest
import wx

from mydata.MyData import MyDataFrame
from mydata.models.settings import SettingsModel


class MyDataMainFrameTester(unittest.TestCase):
    """
    Test ability to display MyData's main frame.
    """
    def setUp(self):
        self.app = wx.App()
        self.settingsModel = SettingsModel(configPath=None)
        self.mydataFrame = MyDataFrame(
            title="MyData",
            style=wx.DEFAULT_FRAME_STYLE,
            settingsModel=self.settingsModel)
        self.mydataFrame.Show()

    def tearDown(self):
        self.mydataFrame.Destroy()

    def test_mydata_main_frame(self):
        """
        Test ability to display MyData's main frame.
        """
        pass


if __name__ == '__main__':
    unittest.main()

"""
Test ability to display MyData's main frame.
"""
import unittest
import wx

from ...MyData import MyDataFrame
from ...models.settings import SettingsModel


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

    def tearDown(self):
        self.mydataFrame.Hide()
        self.mydataFrame.Destroy()

    def test_mydata_main_frame(self):
        """
        Test ability to display MyData's main frame.
        """
        self.mydataFrame.Show()


if __name__ == '__main__':
    unittest.main()

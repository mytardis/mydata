"""
Test ability to perform connectivity check.
"""
import unittest
import wx

from mydata.models.settings import SettingsModel
from mydata.events import MyDataEvent
from mydata.events import EVT_CHECK_CONNECTIVITY


class ConnectivityCheckTester(unittest.TestCase):
    """
    Test ability to perform connectivity check.
    """
    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title="Connectivity check test")
        self.settingsModel = SettingsModel(configPath=None)

    def tearDown(self):
        self.frame.Destroy()

    def test_connectivity_check(self):
        """
        Test ability to perform connectivity check.
        """
        event = MyDataEvent(EVT_CHECK_CONNECTIVITY,
                            settingsModel=self.settingsModel)
        MyDataEvent.CheckConnectivity(event)


if __name__ == '__main__':
    unittest.main()

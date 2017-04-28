"""
Test ability to perform connectivity check.
"""
import unittest
import wx

import mydata.events as mde
from ...settings import SETTINGS
from ...models.settings import SettingsModel
from ...utils.connectivity import CONNECTIVITY


class ConnectivityCheckTester(unittest.TestCase):
    """
    Test ability to perform connectivity check.
    """
    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title="Connectivity check test")
        mde.MYDATA_EVENTS.InitializeWithNotifyWindow(self.frame)
        SETTINGS.Update(SettingsModel(configPath=None))

    def tearDown(self):
        self.frame.Destroy()

    def test_connectivity_check(self):
        """
        Test ability to perform connectivity check.
        """
        event = mde.MYDATA_EVENTS.CheckConnectivityEvent()
        mde.CheckConnectivity(event)
        self.assertTrue(CONNECTIVITY.lastCheckSuccess)
        self.assertFalse(CONNECTIVITY.NeedToCheck())

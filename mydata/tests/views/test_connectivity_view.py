"""
Test ability to open connectivity view.
"""
import unittest
import wx

from ...utils.exceptions import NoActiveNetworkInterface
from ...views.connectivity import ReportNoActiveInterfaces


class ConnectivityViewTester(unittest.TestCase):
    """
    Test ability to open connectivity view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)
        self.app.SetAppName('ConnectivityViewTester')
        self.frame = wx.Frame(None, title='ConnectivityViewTester')
        self.frame.Show()

    def test_connectivity_view(self):
        """Test ability to open connectivity view.
        """
        with self.assertRaises(NoActiveNetworkInterface):
            ReportNoActiveInterfaces()

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()

"""
Test ability to access MyData's online documentation.
"""
import unittest

import wx

from ...MyData import MyData


class MyDataOnlineDocsTester(unittest.TestCase):
    """
    Test ability to access MyData's online documentation.
    """
    def __init__(self, *args, **kwargs):
        super(MyDataOnlineDocsTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def test_mydata_online_docs(self):
        """
        Test ability to access MyData's online documentation.
        """
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'],
                                promptForMissingSettings=False)
        pyEvent = wx.PyEvent()
        self.mydataApp.OnHelp(pyEvent)
        self.mydataApp.OnWalkthrough(pyEvent)

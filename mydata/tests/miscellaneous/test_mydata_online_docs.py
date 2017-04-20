"""
Test ability to access MyData's online documentation.
"""
import os

import wx

from ...MyData import MyData
from .. import MyDataMinimalTester


class MyDataOnlineDocsTester(MyDataMinimalTester):
    """
    Test ability to access MyData's online documentation.
    """
    def __init__(self, *args, **kwargs):
        super(MyDataOnlineDocsTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(MyDataOnlineDocsTester, self).setUp()
        os.environ['MYDATA_DONT_RUN_SCHEDULE'] = 'True'

    def tearDown(self):
        super(MyDataOnlineDocsTester, self).tearDown()
        del os.environ['MYDATA_DONT_RUN_SCHEDULE']

    def test_mydata_online_docs(self):
        """
        Test ability to access MyData's online documentation.
        """
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        pyEvent = wx.PyEvent()
        self.mydataApp.frame.OnHelp(pyEvent)
        self.mydataApp.frame.OnWalkthrough(pyEvent)

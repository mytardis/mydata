"""
Test ability to access MyData's online documentation.
"""
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

    def test_mydata_online_docs(self):
        """
        Test ability to access MyData's online documentation.
        """
        self.mydataApp = MyData(
            argv=['MyData', '--loglevel', 'DEBUG'],
            okToShowModalDialogs=False, okToRunSchedule=False)
        pyEvent = wx.PyEvent()
        self.mydataApp.OnHelp(pyEvent)
        self.mydataApp.OnWalkthrough(pyEvent)

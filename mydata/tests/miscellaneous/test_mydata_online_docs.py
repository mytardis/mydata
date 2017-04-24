"""
Test ability to access MyData's online documentation.
"""
import wx

from ...events.docs import OnHelp
from ...events.docs import OnWalkthrough
from .. import MyDataMinimalTester


class MyDataOnlineDocsTester(MyDataMinimalTester):
    """
    Test ability to access MyData's online documentation.
    """
    def test_mydata_online_docs(self):
        """
        Test ability to access MyData's online documentation.
        """
        assert self  # Avoid Pylint's no-self-use
        pyEvent = wx.PyEvent()
        OnHelp(pyEvent)
        OnWalkthrough(pyEvent)

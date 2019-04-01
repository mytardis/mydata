"""
Test ability to access MyData's online documentation.

http://mydata.readthedocs.org/en/latest/
http://mydata.readthedocs.org/en/latest/macosx-walkthrough.html
http://mydata.readthedocs.org/en/latest/settings.html
"""
from mock import patch
import wx

from ...events.docs import OnHelp
from ...events.docs import OnWalkthrough
from .. import MyDataMinimalTester


class MyDataOnlineDocsTester(MyDataMinimalTester):
    """
    Test ability to access MyData's online documentation.
    """
    def test_mydata_online_docs(self):
        """Test ability to access MyData's online documentation
        """
        assert self  # Avoid Pylint's no-self-use
        pyEvent = wx.PyEvent()

        with patch("webbrowser.open") as mockWebbrowserOpen:
            OnHelp(pyEvent)
            mockWebbrowserOpen.assert_called_once_with(
                "http://mydata.readthedocs.org/en/latest/", 2, True)

        with patch("webbrowser.open") as mockWebbrowserOpen:
            OnWalkthrough(pyEvent)
            mockWebbrowserOpen.assert_called_once_with(
                "http://mydata.readthedocs.org/en/latest/macosx-walkthrough.html",
                2, True)

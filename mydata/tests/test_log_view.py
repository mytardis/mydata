"""
Test ability to open log view.
"""
import unittest
import logging
import wx

from mydata.views.log import LogView

logger = logging.getLogger(__name__)


class LogViewTester(unittest.TestCase):
    """
    Test ability to open log view.
    """
    def test_tasks_view(self):
        """
        Test ability to open log view.
        """
        # pylint: disable=no-self-use

        app = wx.App(redirect=False)  # pylint: disable=unused-variable
        frame = wx.Frame(None)
        settingsModel = None
        LogView(frame, settingsModel)
        frame.Show()
        frame.Destroy()

"""
Test ability to open log view.
"""
import unittest
import logging

import wx

from ...views.log import LogView
from ...logs import logger


class LogViewTester(unittest.TestCase):
    """
    Test ability to open log view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)
        self.app.SetAppName('LogViewTester')
        self.frame = wx.Frame(None, title='LogViewTester')
        self.frame.Show()

    def test_log_view(self):
        """Test ability to open log view.
        """
        logView = LogView(self.frame)
        pyCommandEvent = wx.PyCommandEvent(wx.wxEVT_COMMAND_CHECKBOX_CLICKED)
        logView.debugCheckBox.SetValue(True)
        logView.OnDebugLogging(pyCommandEvent)
        self.assertEqual(logger.GetLevel(), logging.DEBUG)
        logView.debugCheckBox.SetValue(False)
        logView.OnDebugLogging(pyCommandEvent)
        self.assertEqual(logger.GetLevel(), logging.INFO)

    def tearDown(self):
        self.frame.Hide()

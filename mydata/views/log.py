"""
Represents the Log tab of MyData's main window,
and the log text displayed within that tab view.
"""
import sys
import logging
import wx

from ..settings import SETTINGS
from ..logs import logger


class LogView(wx.Panel):
    """
    Represents the Log tab of MyData's main window,
    and the log text displayed within that tab view.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.parent = parent
        self.logTextCtrl = wx.TextCtrl(self, wx.ID_ANY,
                                       style=wx.TE_MULTILINE | wx.TE_READONLY)

        logPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=0, hgap=0)
        logPanelSizer.AddGrowableRow(0)
        logPanelSizer.AddGrowableCol(0)
        logPanelSizer.Add(self.logTextCtrl, flag=wx.EXPAND)
        footerPanel = wx.Panel(self)
        footerPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=0, hgap=20)
        self.clearLogButton = wx.Button(footerPanel, wx.ID_ANY, "Clear log")
        self.Bind(wx.EVT_BUTTON, self.OnClearLog)
        self.submitDebugLogButton = wx.Button(footerPanel, wx.ID_ANY, "Submit debug log")
        self.Bind(wx.EVT_BUTTON, self.OnSubmitDebugLog, id=self.submitDebugLogButton.GetId())
        self.debugCheckBox = wx.CheckBox(footerPanel, wx.ID_ANY, "Debug logging")
        if logger.GetLevel() == logging.DEBUG:
            self.debugCheckBox.SetValue(True)
        self.Bind(wx.EVT_CHECKBOX, self.OnDebugLogging, id=self.debugCheckBox.GetId())
        footerPanelSizer.Add(self.clearLogButton, flag=wx.LEFT)
        footerPanelSizer.Add(self.debugCheckBox, flag=wx.ALIGN_CENTER_VERTICAL)
        footerPanelSizer.Add(self.submitDebugLogButton)
        footerPanel.SetSizerAndFit(footerPanelSizer)
        logPanelSizer.Add(footerPanel,
                          flag=wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM | wx.RIGHT,
                          border=2)
        self.SetSizer(logPanelSizer)
        if sys.platform.startswith("darwin"):
            font = wx.Font(13, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        else:
            font = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        self.logTextCtrl.SetFont(font)

        logger.SendLogMessagesToDebugWindowTextControl(self.logTextCtrl)

    def OnClearLog(self, event):
        """
        Clear debug log output window
        """
        # pylint: disable=unused-argument
        self.logTextCtrl.SetValue("")

    def OnSubmitDebugLog(self, event):
        """
        Called when user presses "Submit debug log" button at the bottom of
        the Log view.  Opens a dialog, so that the user can add a comment
        and confirm that they want to POST a debug log to the server
        (currently hard-coded to be a server managed by the MyData core
        developers - https://cvl.massive.org.au).
        """
        logger.SubmitLog(self.parent, SETTINGS)
        event.Skip()

    def OnDebugLogging(self, event):
        """
        Turn debug-level logging on or off.
        """
        if self.debugCheckBox.IsChecked():
            logger.SetLevel(logging.DEBUG)
        else:
            logger.SetLevel(logging.INFO)
        event.Skip()

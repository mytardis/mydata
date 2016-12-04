"""
Represents the Log tab of MyData's main window,
and the log text displayed within that tab view.
"""
import sys
import logging
import wx

from mydata.logs import logger


class LogView(wx.Panel):
    """
    Represents the Log tab of MyData's main window,
    and the log text displayed within that tab view.
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, parent, settingsModel):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.parent = parent
        self.settingsModel = settingsModel
        self.logTextCtrl = wx.TextCtrl(self, wx.ID_ANY,
                                       style=wx.TE_MULTILINE | wx.TE_READONLY)

        logPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=0, hgap=0)
        logPanelSizer.AddGrowableRow(0)
        logPanelSizer.AddGrowableCol(0)
        logPanelSizer.Add(self.logTextCtrl, flag=wx.EXPAND)
        footerPanel = wx.Panel(self)
        footerPanelSizer = wx.FlexGridSizer(rows=1, cols=2, vgap=0, hgap=20)
        self.submitDebugLogButton = wx.Button(footerPanel, wx.ID_ANY,
                                              "Submit debug log")
        self.Bind(wx.EVT_BUTTON, self.OnSubmitDebugLog,
                  id=self.submitDebugLogButton.GetId())
        self.debugCheckBox = wx.CheckBox(footerPanel, wx.ID_ANY, "Debug logging")
        self.Bind(wx.EVT_CHECKBOX, self.OnDebugLogging,
                  id=self.debugCheckBox.GetId())
        footerPanelSizer.Add(self.debugCheckBox)
        footerPanelSizer.Add(self.submitDebugLogButton)
        footerPanel.SetSizerAndFit(footerPanelSizer)
        logPanelSizer.Add(footerPanel,
                          flag=wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM | wx.RIGHT,
                          border=2)
        self.SetSizer(logPanelSizer)
        if sys.platform.startswith("darwin"):
            font = wx.Font(13, wx.MODERN, wx.NORMAL, wx.NORMAL, False,
                           u'Courier New')
        else:
            font = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, False,
                           u'Courier New')
        self.logTextCtrl.SetFont(font)

        logger.SendLogMessagesToDebugWindowTextControl(self.logTextCtrl)

    def OnSubmitDebugLog(self, event):
        """
        Called when user presses "Submit debug log" button at the bottom of
        the Log view.  Opens a dialog, so that the user can add a comment
        and confirm that they want to POST a debug log to the server
        (currently hard-coded to be a server managed by the MyData core
        developers - https://cvl.massive.org.au).
        """
        logger.SubmitLog(self.parent, self.settingsModel)
        event.Skip()

    def OnDebugLogging(self, event):
        """
        Turn debug-level logging on or off.
        """
        # pylint: disable=no-self-use
        if event.IsChecked():
            logger.SetLevel(logging.DEBUG)
        else:
            logger.SetLevel(logging.INFO)

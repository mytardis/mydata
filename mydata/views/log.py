"""
Represents the Log tab of MyData's main window,
and the log text displayed within that tab view.
"""
import wx
import sys

from mydata.logs import logger


class LogView(wx.Panel):
    """
    Represents the Log tab of MyData's main window,
    and the log text displayed within that tab view.
    """
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
        self.submitDebugLogButton = wx.Button(self, wx.ID_ANY,
                                              "Submit debug log")
        self.Bind(wx.EVT_BUTTON, self.OnSubmitDebugLog,
                  id=self.submitDebugLogButton.GetId())
        logPanelSizer.Add(self.submitDebugLogButton,
                          flag=wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM | wx.RIGHT,
                          border=1)
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
        logger.DumpLog(self.parent, self.settingsModel, submitDebugLog=True)
        event.Skip()

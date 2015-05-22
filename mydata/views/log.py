import wx
import sys

from logger.Logger import logger


class LogView(wx.Panel):

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
        logger.DumpLog(self.parent, self.settingsModel, submitDebugLog=True)

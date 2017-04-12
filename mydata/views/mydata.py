"""
mydata/views/myData.py

Main window for MyData.
"""
import sys

import wx

from ..media import MYDATA_ICONS


class NotebookTabs(object):
    """
    Enumerated data type for referencing the different tab views in
    MyData's main window.
    """
    FOLDERS = 0
    USERS = 1
    GROUPS = 2
    VERIFICATIONS = 3
    UPLOADS = 4
    LOG = 5


class MyDataFrame(wx.Frame):
    """
    MyData's main window.
    """
    def __init__(self, title, style):
        wx.Frame.__init__(self, None, wx.ID_ANY, title, style=style)
        self.SetSize(wx.Size(1000, 600))
        self.statusbar = wx.StatusBar(self)
        if sys.platform.startswith("win"):
            self.statusbar.SetSize(wx.Size(-1, 28))
        else:
            self.statusbar.SetSize(wx.Size(-1, 18))
        self.statusbar.SetFieldsCount(2)
        self.SetStatusBar(self.statusbar)
        self.statusbar.SetStatusWidths([-1, 60])
        self.connectedBitmap = MYDATA_ICONS.GetIcon("Connect")
        self.disconnectedBitmap = MYDATA_ICONS.GetIcon("Disconnect")
        self.connected = False

    def SetStatusMessage(self, msg):
        """
        Update status bar's message.
        """
        if sys.platform.startswith("win"):
            # On Windows, a tab can be used to center status text,
            # which look similar to the old EnhancedStatusBar.
            self.statusbar.SetStatusText("\t%s" % msg)
        else:
            self.statusbar.SetStatusText(msg)
        if sys.platform.startswith("win"):
            if wx.PyApp.IsMainLoopRunning():
                wx.GetApp().taskBarIcon.SetIcon(
                    wx.GetApp().taskBarIcon.icon, msg)

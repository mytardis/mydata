import wx
import os
import sys
import win32com.shell.shell as shell


class MyDataTaskBarIcon(wx.TaskBarIcon):

    def __init__(self, frame):
        """Constructor"""
        wx.TaskBarIcon.__init__(self)
        self.frame = frame

        # img = wx.Image("icon_048.png", wx.BITMAP_TYPE_ANY)
        img = wx.Image("favicon.ico", wx.BITMAP_TYPE_ANY)
        bmp = wx.BitmapFromImage(img)
        self.icon = wx.EmptyIcon()
        self.icon.CopyFromBitmap(bmp)

        self.SetIcon(self.icon, "MyData")

        # Mouse event handling set up in InstrumentApp class's OnInit method.
        # self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.OnTaskBarLeftClick)

    def OnTaskBarActivate(self, evt):
        """"""
        pass

    def OnTaskBarClose(self, evt):
        """
        Destroy the taskbar icon and frame from the taskbar icon itself
        """
        self.frame.Close()

    def CreatePopupMenu(self):

        self.menu = wx.Menu()

        ms = wx.MenuItem(self.menu, wx.NewId(), "MyTardis Sync")
        self.menu.AppendItem(ms)
        self.Bind(wx.EVT_MENU, self.OnMyTardisSync, ms)

        self.menu.AppendSeparator()

        mcp = wx.MenuItem(self.menu, wx.NewId(), "MyData Control Panel")
        self.menu.AppendItem(mcp)
        self.Bind(wx.EVT_MENU, self.OnMyDataControlPanel, mcp)

        self.menu.AppendSeparator()

        mh = wx.MenuItem(self.menu, wx.NewId(), "MyData Help")
        self.menu.AppendItem(mh)
        self.Bind(wx.EVT_MENU, self.OnMyDataHelp, mh)

        self.menu.AppendSeparator()

        mh = wx.MenuItem(self.menu, wx.NewId(), "Exit MyData")
        self.menu.AppendItem(mh)
        self.Bind(wx.EVT_MENU, self.OnExit, mh)

        return self.menu

    def OnMyDataControlPanel(self, event):
        self.frame.Restore()
        self.frame.Raise()

    def OnMyTardisSync(self, event):
        wx.GetApp().OnRefresh(event)

    def OnMyDataHelp(self, event):
        self.frame.Help()

    def OnExit(self, event):
       message = "Are you sure you want to Exit MyData?"
       confirmationDialog = \
           wx.MessageDialog(None, message, "Confirm Exit",
                            wx.YES | wx.NO | wx.ICON_QUESTION)
       okToExit = confirmationDialog.ShowModal()
       if okToExit == wx.ID_YES:
           cmd = "Exit MyData.exe"
           shell.ShellExecuteEx(lpVerb='runas', lpFile=cmd,
                                lpParameters="")
           os._exit(0)

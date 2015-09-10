import wx
import os
import sys
import platform
import webbrowser

from mydata.media import MyDataIcons
from mydata.media import IconStyle


class MyDataTaskBarIcon(wx.TaskBarIcon):
    def __init__(self, frame, settingsModel):
        """Constructor"""
        wx.TaskBarIcon.__init__(self)
        self.frame = frame
        self.settingsModel = settingsModel

        bmp = MyDataIcons.GetIcon("favicon", vendor="MyTardis")
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

        self.myTardisSyncMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "MyTardis Sync")
        self.menu.AppendItem(self.myTardisSyncMenuItem)
        self.Bind(wx.EVT_MENU, self.OnMyTardisSync,
                  self.myTardisSyncMenuItem, self.myTardisSyncMenuItem.GetId())

        self.menu.AppendSeparator()

        self.myTardisControlPanelMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "MyData Control Panel")
        self.menu.AppendItem(self.myTardisControlPanelMenuItem)
        self.Bind(wx.EVT_MENU, self.OnMyDataControlPanel,
                  self.myTardisControlPanelMenuItem)

        self.menu.AppendSeparator()

        self.myTardisHelpMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "MyData Help")
        self.menu.AppendItem(self.myTardisHelpMenuItem)
        self.Bind(wx.EVT_MENU, self.OnMyDataHelp, self.myTardisHelpMenuItem)

        self.menu.AppendSeparator()

        self.exitMyDataMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "Exit MyData")
        self.menu.AppendItem(self.exitMyDataMenuItem)
        self.Bind(wx.EVT_MENU, self.OnExit, self.exitMyDataMenuItem)

        return self.menu

    def GetMyTardisSyncMenuItem(self):
        if hasattr(self, "myTardisSyncMenuItem"):
            return self.myTardisSyncMenuItem
        else:
            return None

    def OnMyDataControlPanel(self, event):
        self.frame.Restore()
        self.frame.Raise()

    def OnMyTardisSync(self, event):
        wx.GetApp().OnRefresh(event)

    def OnMyDataHelp(self, event):
        new = 2  # Open in a new tab, if possible
        url = "http://mydata.readthedocs.org/en/latest/"
        webbrowser.open(url, new=new)

    def OnExit(self, event):
        started = wx.GetApp().foldersController.Started()
        completed = wx.GetApp().foldersController.Completed()
        canceled = wx.GetApp().foldersController.Canceled()
        failed = wx.GetApp().foldersController.Failed()

        message = "Are you sure you want to close MyData?"
        if started and not completed and not canceled and not failed:
            message += "\n\n" \
                "MyData will attempt to shut down any uploads currently " \
                "in progress before exiting."
        confirmationDialog = \
            wx.MessageDialog(None, message, "MyData",
                             wx.YES | wx.NO | wx.ICON_QUESTION)
        okToExit = confirmationDialog.ShowModal()
        if okToExit == wx.ID_YES:
            if not self.settingsModel.RunningInBackgroundMode():
                os._exit(0)
            if sys.platform.startswith("win"):
                if platform.release() == "XP":
                    os._exit(0)
                import win32com.shell.shell as shell
                if hasattr(sys, "frozen"):
                    cmd = "MyData.exe"
                else:
                    cmd = "Python.exe"
                shell.ShellExecuteEx(lpVerb='runas', lpFile=cmd,
                                     lpParameters="--version")
            elif sys.platform.startswith("darwin"):
                returncode = os.system("osascript -e "
                                       "'do shell script "
                                       "\"echo Exiting MyData\" "
                                       "with administrator privileges'")
                if returncode != 0:
                    raise Exception("Failed to get admin privileges.")
            os._exit(0)

import wx
try:
    from wx import TaskBarIcon
except ImportError:
    from wx.adv import TaskBarIcon
import os
import sys
import platform
import webbrowser

from mydata.media import MyDataIcons
from mydata.media import IconStyle
from mydata.logs import logger
from mydata.models.settings import LastSettingsWriteMethod


class MyDataTaskBarIcon(TaskBarIcon):
    def __init__(self, frame, settingsModel):
        """Constructor"""
        TaskBarIcon.__init__(self)
        self.frame = frame
        self.settingsModel = settingsModel

        bmp = MyDataIcons.GetIcon("favicon", vendor="MyTardis")
        self.icon = wx.EmptyIcon()
        self.icon.CopyFromBitmap(bmp)

        self.SetIcon(self.icon, "MyData")

        # Mouse event handling set up in MyData class's OnInit method.
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

        self.myTardisMainWindowMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "MyData Main Window")
        self.menu.AppendItem(self.myTardisMainWindowMenuItem)
        self.Bind(wx.EVT_MENU, self.OnMyDataMainWindow,
                  self.myTardisMainWindowMenuItem)

        self.myTardisSettingsMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "MyData Settings")
        self.menu.AppendItem(self.myTardisSettingsMenuItem)
        self.Bind(wx.EVT_MENU, self.OnMyDataSettings,
                  self.myTardisSettingsMenuItem)

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

    def OnMyDataMainWindow(self, event):
        self.frame.Show(True)
        self.frame.Raise()

    def OnMyDataSettings(self, event):
        self.frame.Show(True)
        self.frame.Raise()
        wx.GetApp().OnSettings(event)

    def OnMyTardisSync(self, event):
        # wx.GetApp().OnRefresh(event)
        logger.debug("MyTardis Sync called from task bar menu item.")
        app = wx.GetApp()
        app.tasksModel.DeleteAllRows()
        app.settingsModel.SetScheduleType("Immediately")
        app.settingsModel.SetLastSettingsWriteMethod(
            LastSettingsWriteMethod.TASKBAR_MENU_ITEM)
        app.ApplySchedule(event)

    def OnMyDataHelp(self, event):
        new = 2  # Open in a new tab, if possible
        url = "http://mydata.readthedocs.org/en/latest/"
        webbrowser.open(url, new=new)

    def OnExit(self, event):
        started = wx.GetApp().foldersController.Started()
        completed = wx.GetApp().foldersController.Completed()
        canceled = wx.GetApp().foldersController.Canceled()
        failed = wx.GetApp().foldersController.Failed()

        self.frame.Show(True)
        self.frame.Raise()
        message = "Are you sure you want to quit MyData?"
        if started and not completed and not canceled and not failed:
            message += "\n\n" \
                "MyData will attempt to shut down any uploads currently " \
                "in progress before exiting."
        confirmationDialog = \
            wx.MessageDialog(self.frame, message, "MyData",
                             wx.YES | wx.NO | wx.ICON_QUESTION)
        okToExit = confirmationDialog.ShowModal()
        if okToExit == wx.ID_YES:
            # See also: wx.GetApp().ShutDownCleanlyAndExit(event)
            os._exit(0)

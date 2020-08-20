
"""
mydata/views/taskbaricon.py

Provides a system tray icon (Windows)
or menubar icon (Mac OS X) for MyData.
"""
import webbrowser

import wx

from ..events.start import ManuallyTriggerScanFoldersAndUpload
from ..events.settings import OnSettings
from ..media import MYDATA_ICONS
from ..logs import logger

if 'phoenix' in wx.PlatformInfo:
    from wx import Icon as EmptyIcon
    from wx.adv import TaskBarIcon
else:
    from wx import EmptyIcon
    from wx import TaskBarIcon


class MyDataTaskBarIcon(TaskBarIcon):
    """
    Provides a system tray icon (Windows)
    or menubar icon (Mac OS X) for MyData.
    """
    def __init__(self, frame):
        """Constructor"""
        TaskBarIcon.__init__(self)
        self.frame = frame

        bmp = MYDATA_ICONS.GetIcon("favicon", vendor="MyTardis")
        self.icon = EmptyIcon()
        self.icon.CopyFromBitmap(bmp)

        self.SetIcon(self.icon, "MyData")

        # Mouse event handling set up in MyData class's OnInit method.
        # self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.OnTaskBarLeftClick)

        self.menu = None
        self.aboutMyDataMenuItem = None
        self.syncNowMenuItem = None
        self.myTardisMainWindowMenuItem = None
        self.myTardisSettingsMenuItem = None
        self.myTardisHelpMenuItem = None
        self.exitMyDataMenuItem = None

    def CreatePopupMenu(self):
        """
        Overrides method in parent class to provide a Popup Menu
        when the user clicks on MyData's system tray (or menubar) icon.
        """
        self.menu = wx.Menu()

        self.aboutMyDataMenuItem = wx.MenuItem(
            self.menu, wx.ID_ANY, "About MyData")
        if 'phoenix' in wx.PlatformInfo:
            self.menu.Append(self.aboutMyDataMenuItem)
        else:
            self.menu.AppendItem(self.aboutMyDataMenuItem)
        self.Bind(wx.EVT_MENU, self.frame.OnAbout,
                  self.aboutMyDataMenuItem, self.aboutMyDataMenuItem.GetId())

        self.menu.AppendSeparator()

        self.syncNowMenuItem = wx.MenuItem(
            self.menu, wx.ID_ANY, "Sync Now")
        if 'phoenix' in wx.PlatformInfo:
            self.menu.Append(self.syncNowMenuItem)
        else:
            self.menu.AppendItem(self.syncNowMenuItem)
        self.Bind(wx.EVT_MENU, MyDataTaskBarIcon.OnSyncNow,
                  self.syncNowMenuItem, self.syncNowMenuItem.GetId())

        self.menu.AppendSeparator()

        self.myTardisMainWindowMenuItem = wx.MenuItem(
            self.menu, wx.ID_ANY, "MyData Main Window")
        if 'phoenix' in wx.PlatformInfo:
            self.menu.Append(self.myTardisMainWindowMenuItem)
        else:
            self.menu.AppendItem(self.myTardisMainWindowMenuItem)
        self.Bind(wx.EVT_MENU, self.OnMyDataMainWindow,
                  self.myTardisMainWindowMenuItem)

        self.myTardisSettingsMenuItem = wx.MenuItem(
            self.menu, wx.ID_ANY, "MyData Settings")
        if 'phoenix' in wx.PlatformInfo:
            self.menu.Append(self.myTardisSettingsMenuItem)
        else:
            self.menu.AppendItem(self.myTardisSettingsMenuItem)
        self.Bind(wx.EVT_MENU, self.OnMyDataSettings,
                  self.myTardisSettingsMenuItem)

        self.menu.AppendSeparator()

        self.myTardisHelpMenuItem = wx.MenuItem(
            self.menu, wx.ID_ANY, "MyData Help")
        if 'phoenix' in wx.PlatformInfo:
            self.menu.Append(self.myTardisHelpMenuItem)
        else:
            self.menu.AppendItem(self.myTardisHelpMenuItem)
        self.Bind(wx.EVT_MENU, MyDataTaskBarIcon.OnMyDataHelp,
                  self.myTardisHelpMenuItem)

        self.menu.AppendSeparator()

        self.exitMyDataMenuItem = wx.MenuItem(
            self.menu, wx.ID_ANY, "Exit MyData")
        if 'phoenix' in wx.PlatformInfo:
            self.menu.Append(self.exitMyDataMenuItem)
        else:
            self.menu.AppendItem(self.exitMyDataMenuItem)
        self.Bind(wx.EVT_MENU, self.OnExit, self.exitMyDataMenuItem)

        return self.menu

    def GetSyncNowMenuItem(self):
        """
        Returns the "Sync Now" menu item.
        """
        return getattr(self, "syncNowMenuItem", None)

    def OnMyDataMainWindow(self, event):
        """
        Called when the "MyData Main Window" menu item is
        selected from MyData's system tray / menu bar icon menu.
        """
        self.frame.Show(True)
        self.frame.Iconize(False)
        self.frame.Raise()
        event.Skip()

    def OnMyDataSettings(self, event):
        """
        Called when the "MyData Settings" menu item is
        selected from MyData's system tray / menu bar icon menu.
        """
        self.frame.Show(True)
        self.frame.Iconize(False)
        self.frame.Raise()
        OnSettings(event)
        event.Skip()

    @staticmethod
    def OnSyncNow(event):
        """
        Called when the "Sync Now" menu item is
        selected from MyData's system tray / menu bar icon menu.
        """
        logger.debug("Sync Now called from task bar menu item.")
        ManuallyTriggerScanFoldersAndUpload(event)

    @staticmethod
    def OnMyDataHelp(event):
        """
        Called when the "MyData Help" menu item is
        selected from MyData's system tray / menu bar icon menu.
        """
        new = 2  # Open in a new tab, if possible
        url = "http://mydata.readthedocs.org/en/latest/"
        webbrowser.open(url, new=new)
        event.Skip()

    def OnExit(self, event):
        """
        Called when the "Exit MyData" menu item is
        selected from MyData's system tray / menu bar icon menu.
        """
        self.frame.Show(True)
        self.frame.Iconize(False)
        self.frame.Raise()
        okToExit = True
        if wx.GetApp().Processing():
            message = "Are you sure you want to quit MyData?\n\n" \
                "MyData will attempt to shut down any uploads currently " \
                "in progress before exiting."
            okToExit = wx.MessageDialog(
                self.frame,
                message,
                "MyData",
                wx.YES | wx.NO | wx.ICON_QUESTION
            ).ShowModal() == wx.ID_YES
        if okToExit:
            wx.GetApp().ShutDownCleanlyAndExit(event, confirm=False)
        event.StopPropagation()

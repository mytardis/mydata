
"""
mydata/views/taskbaricon.py

Provides a system tray icon (Windows)
or menubar icon (Mac OS X) for MyData.
"""

# pylint: disable=wrong-import-position

import webbrowser

import wx
if wx.version().startswith("3.0.3.dev"):
    from wx import Icon as EmptyIcon
    # pylint: disable=import-error
    # pylint: disable=no-name-in-module
    from wx.adv import TaskBarIcon
else:
    from wx import EmptyIcon
    from wx import TaskBarIcon

from mydata.media import MYDATA_ICONS
from mydata.logs import logger


class MyDataTaskBarIcon(TaskBarIcon):
    """
    Provides a system tray icon (Windows)
    or menubar icon (Mac OS X) for MyData.
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, frame, settingsModel):
        """Constructor"""
        TaskBarIcon.__init__(self)
        self.frame = frame
        self.settingsModel = settingsModel

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
            self.menu, wx.NewId(), "About MyData")
        if wx.version().startswith("3.0.3.dev"):
            self.menu.Append(self.aboutMyDataMenuItem)
        else:
            self.menu.AppendItem(self.aboutMyDataMenuItem)
        self.Bind(wx.EVT_MENU, wx.GetApp().OnAbout,
                  self.aboutMyDataMenuItem, self.aboutMyDataMenuItem.GetId())

        self.menu.AppendSeparator()

        self.syncNowMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "Sync Now")
        if wx.version().startswith("3.0.3.dev"):
            self.menu.Append(self.syncNowMenuItem)
        else:
            self.menu.AppendItem(self.syncNowMenuItem)
        self.Bind(wx.EVT_MENU, self.OnSyncNow,
                  self.syncNowMenuItem, self.syncNowMenuItem.GetId())

        self.menu.AppendSeparator()

        self.myTardisMainWindowMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "MyData Main Window")
        if wx.version().startswith("3.0.3.dev"):
            self.menu.Append(self.myTardisMainWindowMenuItem)
        else:
            self.menu.AppendItem(self.myTardisMainWindowMenuItem)
        self.Bind(wx.EVT_MENU, self.OnMyDataMainWindow,
                  self.myTardisMainWindowMenuItem)

        self.myTardisSettingsMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "MyData Settings")
        if wx.version().startswith("3.0.3.dev"):
            self.menu.Append(self.myTardisSettingsMenuItem)
        else:
            self.menu.AppendItem(self.myTardisSettingsMenuItem)
        self.Bind(wx.EVT_MENU, self.OnMyDataSettings,
                  self.myTardisSettingsMenuItem)

        self.menu.AppendSeparator()

        self.myTardisHelpMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "MyData Help")
        if wx.version().startswith("3.0.3.dev"):
            self.menu.Append(self.myTardisHelpMenuItem)
        else:
            self.menu.AppendItem(self.myTardisHelpMenuItem)
        self.Bind(wx.EVT_MENU, self.OnMyDataHelp, self.myTardisHelpMenuItem)

        self.menu.AppendSeparator()

        self.exitMyDataMenuItem = wx.MenuItem(
            self.menu, wx.NewId(), "Exit MyData")
        if wx.version().startswith("3.0.3.dev"):
            self.menu.Append(self.exitMyDataMenuItem)
        else:
            self.menu.AppendItem(self.exitMyDataMenuItem)
        self.Bind(wx.EVT_MENU, self.OnExit, self.exitMyDataMenuItem)

        return self.menu

    def GetSyncNowMenuItem(self):
        """
        Returns the "Sync Now" menu item.
        """
        if hasattr(self, "syncNowMenuItem"):
            return self.syncNowMenuItem
        else:
            return None

    def OnMyDataMainWindow(self, event):
        """
        Called when the "MyData Main Window" menu item is
        selected from MyData's system tray / menu bar icon menu.
        """
        self.frame.Show(True)
        self.frame.Raise()
        event.Skip()

    def OnMyDataSettings(self, event):
        """
        Called when the "MyData Settings" menu item is
        selected from MyData's system tray / menu bar icon menu.
        """
        self.frame.Show(True)
        self.frame.Raise()
        wx.GetApp().OnSettings(event)
        event.Skip()

    # pylint: disable=no-self-use
    def OnSyncNow(self, event):
        """
        Called when the "Sync Now" menu item is
        selected from MyData's system tray / menu bar icon menu.
        """
        logger.debug("Sync Now called from task bar menu item.")
        wx.GetApp().ScanFoldersAndUpload(event)

    # pylint: disable=no-self-use
    def OnMyDataHelp(self, event):
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
        self.frame.Raise()
        message = "Are you sure you want to quit MyData?"
        if wx.GetApp().Processing():
            message += "\n\n" \
                "MyData will attempt to shut down any uploads currently " \
                "in progress before exiting."
        confirmationDialog = \
            wx.MessageDialog(self.frame, message, "MyData",
                             wx.YES | wx.NO | wx.ICON_QUESTION)
        okToExit = confirmationDialog.ShowModal()
        if okToExit == wx.ID_YES:
            wx.GetApp().ShutDownCleanlyAndExit(event, confirm=False)
        event.Skip()

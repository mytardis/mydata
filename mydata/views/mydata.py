"""
mydata/views/mydata.py

Main window for MyData.
"""
import sys
import traceback

import wx

from ..logs import logger
from ..media import MYDATA_ICONS
from ..utils import OpenUrl
from ..events.docs import OnHelp
from ..events.docs import OnWalkthrough
from .dataview import MyDataDataView
from .log import LogView
from .taskbaricon import MyDataTaskBarIcon
from .toolbar import MyDataToolbar

if 'phoenix' in wx.PlatformInfo:
    from wx import Icon as EmptyIcon
    from wx.adv import EVT_TASKBAR_LEFT_UP
    from wx.adv import EVT_TASKBAR_LEFT_DOWN
    from wx.lib.agw.aui import AuiNotebook
    from wx.lib.agw.aui import AUI_NB_TOP
    from wx.lib.agw.aui import EVT_AUINOTEBOOK_PAGE_CHANGING
else:
    from wx import EmptyIcon
    from wx import EVT_TASKBAR_LEFT_UP
    from wx import EVT_TASKBAR_LEFT_DOWN
    from wx.aui import AuiNotebook
    from wx.aui import AUI_NB_TOP
    from wx.aui import EVT_AUINOTEBOOK_PAGE_CHANGING


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
    def __init__(self, title, dataViewModels):
        wx.Frame.__init__(self, None, wx.ID_ANY, title)
        self.SetSize(wx.Size(1000, 600))
        self.statusbar = wx.StatusBar(self)
        if sys.platform.startswith("win"):
            self.statusbar.SetSize(wx.Size(-1, 28))
        else:
            self.statusbar.SetSize(wx.Size(-1, 18))
        self.statusbar.SetFieldsCount(2)
        self.SetStatusBar(self.statusbar)
        self.statusbar.SetStatusWidths([-1, 60])

        self.mydataApp = wx.GetApp()
        self.dataViewModels = dataViewModels

        self.panel = wx.Panel(self)

        if sys.platform.startswith("darwin"):
            self.CreateMacMenu()

        self.toolbar = MyDataToolbar(self)

        bmp = MYDATA_ICONS.GetIcon("favicon", vendor="MyTardis")
        icon = EmptyIcon()
        icon.CopyFromBitmap(bmp)
        self.SetIcon(icon)

        self.panel = wx.Panel(self)

        if 'phoenix' in wx.PlatformInfo:
            self.tabbedView = AuiNotebook(self.panel, agwStyle=AUI_NB_TOP)
        else:
            self.tabbedView = AuiNotebook(self.panel, style=AUI_NB_TOP)
        # Without the following line, the tab font looks
        # too small on Mac OS X:
        self.tabbedView.SetFont(self.panel.GetFont())
        self.Bind(EVT_AUINOTEBOOK_PAGE_CHANGING,
                  self.OnNotebookPageChanging, self.tabbedView)

        self.dataViews = dict()
        if self.dataViewModels:
            self.AddDataViews()

        self.logView = LogView(self.tabbedView)
        self.tabbedView.AddPage(self.logView, "Log")

        sizer = wx.BoxSizer()
        sizer.Add(self.tabbedView, 1, flag=wx.EXPAND)
        self.panel.SetSizer(sizer)

        sizer = wx.BoxSizer()
        sizer.Add(self.panel, 1, flag=wx.EXPAND)
        self.SetSizer(sizer)

        self.tabbedView.SendSizeEvent()

        self.panel.SetFocus()

        self.taskBarIcon = MyDataTaskBarIcon(self)
        if sys.platform.startswith("linux"):
            self.taskBarIcon.Bind(EVT_TASKBAR_LEFT_DOWN, self.OnTaskBarLeftClick)
        else:
            self.taskBarIcon.Bind(EVT_TASKBAR_LEFT_UP, self.OnTaskBarLeftClick)

        self.Bind(wx.EVT_MENU, self.taskBarIcon.OnExit, id=wx.ID_EXIT)

        self.Bind(wx.EVT_CLOSE, self.OnCloseFrame)
        self.Bind(wx.EVT_ICONIZE, self.OnMinimizeFrame)

    def AddDataViews(self):
        """
        Create data views and add them to tabbed view.
        """
        self.dataViews['folders'] = MyDataDataView(
            self.tabbedView, self.dataViewModels['folders'])
        self.tabbedView.AddPage(self.dataViews['folders'], "Folders")

        self.dataViews['users'] = MyDataDataView(
            self.tabbedView, self.dataViewModels['users'])
        self.tabbedView.AddPage(self.dataViews['users'], "Users")

        self.dataViews['groups'] = MyDataDataView(
            self.tabbedView, self.dataViewModels['groups'])
        self.tabbedView.AddPage(self.dataViews['groups'], "Groups")

        self.dataViews['verifications'] = MyDataDataView(
            self.tabbedView, self.dataViewModels['verifications'])
        self.tabbedView.AddPage(
            self.dataViews['verifications'], "Verifications")

        self.dataViews['uploads'] = MyDataDataView(
            self.tabbedView, self.dataViewModels['uploads'])
        self.tabbedView.AddPage(self.dataViews['uploads'], "Uploads")

        self.dataViews['tasks'] = MyDataDataView(
            self.tabbedView, self.dataViewModels['tasks'])
        self.tabbedView.AddPage(self.dataViews['tasks'], "Tasks")

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
                self.mydataApp.taskBarIcon.SetIcon(
                    self.mydataApp.taskBarIcon.icon, msg)

    def CreateMacMenu(self):
        """
        On Mac OS X, adding an Edit menu seems to help with
        enabling command-c (copy) and command-v (paste)
        """
        menuBar = wx.MenuBar()
        editMenu = wx.Menu()
        editMenu.Append(wx.ID_UNDO, "Undo\tCTRL+Z", "Undo")
        editMenu.Append(wx.ID_REDO, "Redo\tCTRL+SHIFT+Z", "Redo")
        editMenu.AppendSeparator()
        editMenu.Append(wx.ID_CUT, "Cut\tCTRL+X", "Cut the selected text")
        editMenu.Append(wx.ID_COPY, "Copy\tCTRL+C", "Copy the selected text")
        editMenu.Append(wx.ID_PASTE, "Paste\tCTRL+V",
                        "Paste text from the clipboard")
        editMenu.Append(wx.ID_SELECTALL, "Select All\tCTRL+A", "Select All")
        menuBar.Append(editMenu, "Edit")

        helpMenu = wx.Menu()

        helpMenuItemID = wx.NewId()
        helpMenu.Append(helpMenuItemID, "&MyData Help")
        self.Bind(wx.EVT_MENU, OnHelp, id=helpMenuItemID)

        walkthroughMenuItemID = wx.NewId()
        helpMenu.Append(walkthroughMenuItemID, "Mac OS X &Walkthrough")
        self.Bind(
            wx.EVT_MENU, OnWalkthrough, id=walkthroughMenuItemID)

        helpMenu.Append(wx.ID_ABOUT, "&About MyData")
        self.Bind(wx.EVT_MENU, MyDataFrame.OnAbout, id=wx.ID_ABOUT)
        menuBar.Append(helpMenu, "&Help")
        self.SetMenuBar(menuBar)

    def OnNotebookPageChanging(self, event):
        """
        Clear the search field after switching views
        (e.g. from Folders to Users).
        """
        if self.toolbar.searchCtrl:
            self.toolbar.searchCtrl.SetValue("")
        event.Skip()

    def OnDoSearch(self, event):
        """
        Triggered by user typing into search field in upper-right corner
        or main window.
        """
        if self.tabbedView.GetSelection() == NotebookTabs.FOLDERS:
            self.dataViewModels['folders'].Filter(event.GetString())
        elif self.tabbedView.GetSelection() == NotebookTabs.USERS:
            self.dataViewModels['users'].Filter(event.GetString())
        elif self.tabbedView.GetSelection() == NotebookTabs.GROUPS:
            self.dataViewModels['groups'].Filter(event.GetString())

    def OnTaskBarLeftClick(self, event):
        """
        Called when task bar icon is clicked with the left mouse button.
        """
        self.taskBarIcon.PopupMenu(self.taskBarIcon.CreatePopupMenu())
        event.Skip()

    def OnMyTardis(self, event):
        """
        Called when user clicks the Internet Browser icon on the
        main toolbar.
        """
        from ..settings import SETTINGS
        try:
            items = self.dataViews['folders'].dataViewControl.GetSelections()
            rows = [self.dataViewModels['folders'].GetRow(item) for item in items]
            if len(rows) == 1:
                folderRecord = self.dataViewModels['folders'].GetFolderRecord(rows[0])
                if folderRecord.datasetModel is not None:
                    OpenUrl(SETTINGS.general.myTardisUrl + "/" +
                            folderRecord.datasetModel.viewUri)
                else:
                    OpenUrl(SETTINGS.general.myTardisUrl)
            else:
                OpenUrl(SETTINGS.general.myTardisUrl)
        except:
            logger.error(traceback.format_exc())
        event.Skip()

    def OnAbout(self, event):
        """
        Called when the user clicks the Info icon on the
        main toolbar.
        """
        from .. import __version__ as VERSION
        from .. import LATEST_COMMIT
        msg = "MyData is a desktop application" \
              " for uploading data to MyTardis " \
              "(https://github.com/mytardis/mytardis).\n\n" \
              "MyData is being developed at the Monash e-Research Centre " \
              "(Monash University, Australia)\n\n" \
              "MyData is open source (GPL3) software available from " \
              "https://github.com/mytardis/mydata\n\n" \
              "Version:   " + VERSION + "\n" \
              "Commit:  " + LATEST_COMMIT + "\n"
        dlg = wx.MessageDialog(self, msg, "About MyData",
                               wx.OK | wx.ICON_INFORMATION)
        if wx.PyApp.IsMainLoopRunning():
            dlg.ShowModal()
        else:
            sys.stderr.write("\n%s\n" % msg)
        event.Skip()

    def OnCloseFrame(self, event):
        """
        Don't actually close it, just hide it.
        """
        event.StopPropagation()
        if sys.platform.startswith("win"):
            self.Show()  # See: http://trac.wxwidgets.org/ticket/10426
        self.Hide()

    def OnMinimizeFrame(self, event):
        """
        When minimizing, hide the frame so it "minimizes to tray"
        """
        if event.Iconized():
            self.frame.Show()  # See: http://trac.wxwidgets.org/ticket/10426
            self.frame.Hide()
        else:
            self.frame.Show(True)
            self.frame.Raise()
        # event.Skip()

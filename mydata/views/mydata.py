"""
mydata/views/mydata.py

Main window for MyData.
"""
import sys
import threading
import traceback

import wx

from ..constants import APPNAME
from ..logs import logger
from ..media import MYDATA_ICONS
from ..threads.flags import FLAGS
from ..utils import OpenUrl
from ..events.docs import OnHelp
from ..events.docs import OnWalkthrough
from .dataview import MyDataDataView
from .verifications import VerificationsDataView
from ..dataviewmodels.dataview import DATAVIEW_MODELS
from .log import LogView
from .taskbaricon import MyDataTaskBarIcon
from .toolbar import MyDataToolbar
from .tabs import NotebookTabs

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


class MyDataFrame(wx.Frame):
    """
    MyData's main window.
    """
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, APPNAME)
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

        self.panel = wx.Panel(self)

        if sys.platform.startswith("darwin"):
            self.CreateMacMenu()

        self.toolbar = MyDataToolbar(self)

        bmp = MYDATA_ICONS.GetIcon("favicon", vendor="MyTardis")
        icon = EmptyIcon()
        icon.CopyFromBitmap(bmp)
        self.SetIcon(icon)

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
        if DATAVIEW_MODELS:
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

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_ICONIZE, self.OnMinimize)

        self.select = True

    def AddDataViews(self):
        """
        Create data views and add them to tabbed view.
        """
        self.dataViews['folders'] = MyDataDataView(self.tabbedView, "folders")
        self.tabbedView.AddPage(self.dataViews['folders'], "Folders")

        self.dataViews['users'] = MyDataDataView(self.tabbedView, "users")
        self.tabbedView.AddPage(self.dataViews['users'], "Users")

        self.dataViews['groups'] = MyDataDataView(self.tabbedView, "groups")
        self.tabbedView.AddPage(self.dataViews['groups'], "Groups")

        self.dataViews['verifications'] = \
            VerificationsDataView(self.tabbedView)
        self.tabbedView.AddPage(
            self.dataViews['verifications'], "Verifications")

        self.dataViews['uploads'] = MyDataDataView(self.tabbedView, "uploads")
        self.tabbedView.AddPage(self.dataViews['uploads'], "Uploads")

        self.dataViews['tasks'] = MyDataDataView(self.tabbedView, "tasks")
        self.tabbedView.AddPage(self.dataViews['tasks'], "Tasks")

        self.dataViews["cleanup"] = MyDataDataView(self.tabbedView, "cleanup")
        self.dataViews["cleanup"].Bind(wx.EVT_HEADER_CLICK, self.OnHeaderClick)
        self.tabbedView.AddPage(self.dataViews['cleanup'], "Cleanup")

    def OnHeaderClick(self, event):
        if DATAVIEW_MODELS["cleanup"].GetColumnName(event.GetColumn()) == "Select":
            for row in range(0, DATAVIEW_MODELS["cleanup"].GetRowCount()):
                setattr(DATAVIEW_MODELS["cleanup"].rowsData[row], "setDelete", self.select)
            self.dataViews["cleanup"].Refresh()
            self.select = not self.select

    def SetStatusMessage(self, msg, force=False):
        """
        Update status bar's message.
        """
        assert threading.current_thread().name == "MainThread"
        if FLAGS.shouldAbort and not force:
            return
        if sys.platform.startswith("win"):
            # On Windows, a tab can be used to center status text,
            # which look similar to the old EnhancedStatusBar.
            self.statusbar.SetStatusText("\t%s" % msg)
        else:
            self.statusbar.SetStatusText(msg)
        if sys.platform.startswith("win"):
            if wx.PyApp.IsMainLoopRunning():
                self.taskBarIcon.SetIcon(self.taskBarIcon.icon, msg)

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

        helpMenuItemID = wx.Window.NewControlId()
        helpMenu.Append(helpMenuItemID, "&MyData Help")
        self.Bind(wx.EVT_MENU, OnHelp, id=helpMenuItemID)

        walkthroughMenuItemID = wx.Window.NewControlId()
        helpMenu.Append(walkthroughMenuItemID, "Mac OS X &Walkthrough")
        self.Bind(
            wx.EVT_MENU, OnWalkthrough, id=walkthroughMenuItemID)

        helpMenu.Append(wx.ID_ABOUT, "&About MyData")
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
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
            DATAVIEW_MODELS['folders'].Filter(event.GetString())
        elif self.tabbedView.GetSelection() == NotebookTabs.USERS:
            DATAVIEW_MODELS['users'].Filter(event.GetString())
        elif self.tabbedView.GetSelection() == NotebookTabs.GROUPS:
            DATAVIEW_MODELS['groups'].Filter(event.GetString())
        elif self.tabbedView.GetSelection() == NotebookTabs.CLEANUP:
            DATAVIEW_MODELS["cleanup"].Filter(event.GetString())

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
            rows = [DATAVIEW_MODELS['folders'].GetRow(item) for item in items]
            if len(rows) == 1:
                folderRecord = DATAVIEW_MODELS['folders'].GetFolderRecord(rows[0])
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

    def OnClose(self, event):
        """
        Don't let this event propagate to the default handlers which will
        destroy the window and the application.

        If the schedule type is "Manually", "On Startup" or
        "On Settings Saved", call the MyData system tray icon's exit handler,
        which will ask the user to confirm they want to exit MyData, and
        quit if requested.

        If the schedule type is "Once", "Daily", "Weekly" or "Timer",
        closing the window will just minimize MyData to its system tray icon.
        """
        event.StopPropagation()
        from ..settings import SETTINGS
        if SETTINGS.schedule.scheduleType in [
                "Manually", "On Startup", "On Settings Saved"]:
            self.taskBarIcon.OnExit(event)
            return
        if sys.platform.startswith("win"):
            self.Show()  # See: http://trac.wxwidgets.org/ticket/10426
        self.Hide()

    def OnMinimize(self, event):
        """
        When minimizing, hide the frame so it "minimizes to tray"
        """
        if event.Iconized():
            if sys.platform.startswith("win"):
                self.Show()  # See: http://trac.wxwidgets.org/ticket/10426
            self.Hide()
        else:
            if sys.platform.startswith("win"):
                self.Show()
            self.Raise()
        # event.Skip()

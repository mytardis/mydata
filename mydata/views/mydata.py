"""
mydata/views/myData.py

Main window for MyData.
"""
import sys

import wx

from ..media import MYDATA_ICONS
from ..media import IconStyle
from .dataview import MyDataDataView
from .log import LogView
from .taskbaricon import MyDataTaskBarIcon

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
        # R: 44, 4: Too many statements (51/50) (too-many-statements)
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
        from ..MyData import MyData
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
        self.Bind(wx.EVT_MENU, MyData.OnHelp, id=helpMenuItemID)

        walkthroughMenuItemID = wx.NewId()
        helpMenu.Append(walkthroughMenuItemID, "Mac OS X &Walkthrough")
        self.Bind(wx.EVT_MENU, MyData.OnWalkthrough, id=walkthroughMenuItemID)

        helpMenu.Append(wx.ID_ABOUT, "&About MyData")
        self.Bind(wx.EVT_MENU, MyData.OnAbout, id=wx.ID_ABOUT)
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


class MyDataToolbar(object):
    """
    MyData's toolbar.
    """
    def __init__(self, parent):
        self.mydataApp = wx.GetApp()
        self.parent = parent
        self.toolbar = parent.CreateToolBar()
        self.toolbar.SetToolBitmapSize(wx.Size(24, 24))  # sets icon size
        if 'phoenix' in wx.PlatformInfo:
            self.addToolMethod = self.toolbar.AddTool
        else:
            self.addToolMethod = self.toolbar.AddLabelTool

        self.AddOpenFolderTool()

        self.toolbar.AddSeparator()

        # Store this as an instance attribute so we can enable/disable it:
        self.testTool = None
        self.AddTestRunTool()

        self.toolbar.AddSeparator()

        # Store this as an instance attribute so we can enable/disable it:
        self.uploadTool = None
        self.AddUploadTool()

        self.toolbar.AddSeparator()

        # Store this as an instance attribute so we can enable/disable it:
        self.stopTool = None
        self.AddStopTool()

        self.toolbar.AddSeparator()

        # Store this as an instance attribute so we can check whether the
        # Settings dialog was opened by clicking on the toolbar icon:
        self.settingsTool = None
        self.AddSettingsTool()

        self.toolbar.AddSeparator()

        self.AddMyTardisTool()

        self.toolbar.AddSeparator()

        self.AddAboutTool()

        self.toolbar.AddSeparator()

        self.AddHelpTool()

        self.toolbar.AddStretchableSpace()

        self.AddSearchControl()

        self.toolbar.Realize()

    def AddOpenFolderTool(self):
        """
        Add open folder tool
        """
        openIcon = MYDATA_ICONS.GetIcon("Open folder", size="24x24")
        openTool = self.addToolMethod(
            wx.ID_ANY, "Open folder", openIcon, shortHelp="Open folder")
        if hasattr(self.mydataApp, "OnOpen"):
            self.parent.Bind(wx.EVT_MENU, self.mydataApp.OnOpen, openTool)

    def AddTestRunTool(self):
        """
        Add test run tool for starting test run.
        """
        testIcon = MYDATA_ICONS.GetIcon("Test tubes", size="24x24")
        self.testTool = self.addToolMethod(
            wx.ID_ANY, "Test Run", testIcon, shortHelp="Test Run")
        if hasattr(self.mydataApp, "OnTestRunFromToolbar"):
            self.parent.Bind(wx.EVT_TOOL, self.mydataApp.OnTestRunFromToolbar,
                             self.testTool, self.testTool.GetId())

    def AddUploadTool(self):
        """
        Add upload tool
        """
        uploadIcon = MYDATA_ICONS.GetIcon("Upload button", size="24x24")
        self.uploadTool = self.addToolMethod(
            wx.ID_ANY, "Scan and Upload", uploadIcon,
            shortHelp="Scan and Upload")
        if hasattr(self.mydataApp, "OnScanAndUploadFromToolbar"):
            self.parent.Bind(
                wx.EVT_TOOL, self.mydataApp.OnScanAndUploadFromToolbar,
                self.uploadTool, self.uploadTool.GetId())

    def AddStopTool(self):
        """
        Add stop tool for stopping scans and uploads.
        """
        stopIcon = MYDATA_ICONS.GetIcon(
            "Stop sign", size="24x24", style=IconStyle.NORMAL)
        self.stopTool = self.addToolMethod(
            wx.ID_STOP, "Stop", stopIcon, shortHelp="Stop")
        disabledStopIcon = MYDATA_ICONS.GetIcon(
            "Stop sign", size="24x24", style=IconStyle.DISABLED)
        self.toolbar.SetToolDisabledBitmap(
            self.stopTool.GetId(), disabledStopIcon)
        self.toolbar.EnableTool(self.stopTool.GetId(), False)
        if hasattr(self.mydataApp, "OnStop"):
            self.parent.Bind(wx.EVT_TOOL, self.mydataApp.OnStop, self.stopTool,
                             self.stopTool.GetId())

    def AddSettingsTool(self):
        """
        Add settings tool for opening Settings dialog.
        """
        settingsIcon = MYDATA_ICONS.GetIcon("Settings", size="24x24")
        self.settingsTool = self.addToolMethod(
            wx.ID_ANY, "Settings", settingsIcon, shortHelp="Settings")
        if hasattr(self.mydataApp, "OnSettings"):
            self.parent.Bind(
                wx.EVT_TOOL, self.mydataApp.OnSettings, self.settingsTool)

    def AddMyTardisTool(self):
        """
        Add MyTardis tool for opening MyTardis in a web browser.
        """
        internetIcon = MYDATA_ICONS.GetIcon("Internet explorer", size="24x24")
        myTardisTool = self.addToolMethod(wx.ID_ANY, "MyTardis",
                                          internetIcon, shortHelp="MyTardis")
        if hasattr(self.mydataApp, "OnMyTardis"):
            self.parent.Bind(
                wx.EVT_TOOL, self.mydataApp.OnMyTardis, myTardisTool)

    def AddAboutTool(self):
        """
        Add About tool for opening MyData's About dialog.
        """
        from ..MyData import MyData
        aboutIcon = MYDATA_ICONS.GetIcon("About", size="24x24",
                                         style=IconStyle.HOT)
        aboutTool = self.addToolMethod(wx.ID_ANY, "About MyData",
                                       aboutIcon, shortHelp="About MyData")
        self.parent.Bind(wx.EVT_TOOL, MyData.OnAbout, aboutTool)

    def AddHelpTool(self):
        """
        Add Help tool for opening MyData's online help.
        """
        from ..MyData import MyData
        helpIcon = MYDATA_ICONS.GetIcon("Help", size="24x24",
                                        style=IconStyle.HOT)
        helpTool = self.addToolMethod(wx.ID_ANY, "Help", helpIcon,
                                      shortHelp="MyData User Guide")
        self.parent.Bind(wx.EVT_TOOL, MyData.OnHelp, helpTool)

    def AddSearchControl(self):
        """
        Add search control
        """
        self.searchCtrl = wx.SearchCtrl(self.toolbar, size=wx.Size(200, -1),
                                        style=wx.TE_PROCESS_ENTER)
        self.searchCtrl.ShowSearchButton(True)
        self.searchCtrl.ShowCancelButton(True)
        self.parent.Bind(
            wx.EVT_TEXT_ENTER, self.parent.OnDoSearch, self.searchCtrl)
        self.parent.Bind(wx.EVT_TEXT, self.parent.OnDoSearch, self.searchCtrl)
        self.toolbar.AddControl(self.searchCtrl)

    def GetToolEnabled(self, toolId):
        """
        Called to determine whether a tool is enabled (responds to user input).
        """
        return self.toolbar.GetToolEnabled(toolId)

    def EnableTestAndUploadToolbarButtons(self):
        """
        Enables the Test Run and Upload toolbar buttons,
        indicating that MyData is ready to respond to a
        request to start scanning folders and uploading data.
        """
        self.toolbar.EnableTool(self.stopTool.GetId(), False)
        self.toolbar.EnableTool(self.testTool.GetId(), True)
        self.toolbar.EnableTool(self.uploadTool.GetId(), True)

    def DisableTestAndUploadToolbarButtons(self):
        """
        Disables the Test Run and Upload toolbar buttons,
        indicating that MyData is busy scanning folders,
        uploading data, validating settings or performing
        a test run.
        """
        self.toolbar.EnableTool(self.stopTool.GetId(), True)
        self.toolbar.EnableTool(self.testTool.GetId(), False)
        self.toolbar.EnableTool(self.uploadTool.GetId(), False)

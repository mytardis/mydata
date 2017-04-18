"""
mydata/views/myData.py

Main window for MyData.
"""
import sys

import wx

from ..media import MYDATA_ICONS
from ..media import IconStyle

if 'phoenix' in wx.PlatformInfo:
    from wx import Icon as EmptyIcon
else:
    from wx import EmptyIcon


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

        self.mydataApp = wx.GetApp()

        self.menuBar = None
        self.editMenu = None
        self.helpMenu = None

        if sys.platform.startswith("darwin"):
            self.CreateMacMenu()

        self.toolbar = MyDataToolbar(self)

        bmp = MYDATA_ICONS.GetIcon("favicon", vendor="MyTardis")
        icon = EmptyIcon()
        icon.CopyFromBitmap(bmp)
        self.SetIcon(icon)

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
        self.menuBar = wx.MenuBar()
        self.editMenu = wx.Menu()
        self.editMenu.Append(wx.ID_UNDO, "Undo\tCTRL+Z", "Undo")
        self.editMenu.Append(wx.ID_REDO, "Redo\tCTRL+SHIFT+Z", "Redo")
        self.editMenu.AppendSeparator()
        self.editMenu.Append(wx.ID_CUT, "Cut\tCTRL+X",
                             "Cut the selected text")
        self.editMenu.Append(wx.ID_COPY, "Copy\tCTRL+C",
                             "Copy the selected text")
        self.editMenu.Append(wx.ID_PASTE, "Paste\tCTRL+V",
                             "Paste text from the clipboard")
        self.editMenu.Append(wx.ID_SELECTALL, "Select All\tCTRL+A",
                             "Select All")
        self.menuBar.Append(self.editMenu, "Edit")

        self.helpMenu = wx.Menu()

        helpMenuItemID = wx.NewId()
        self.helpMenu.Append(helpMenuItemID, "&MyData Help")
        self.Bind(wx.EVT_MENU, MyData.OnHelp, id=helpMenuItemID)

        walkthroughMenuItemID = wx.NewId()
        self.helpMenu.Append(walkthroughMenuItemID, "Mac OS X &Walkthrough")
        self.Bind(wx.EVT_MENU, MyData.OnWalkthrough, id=walkthroughMenuItemID)

        self.helpMenu.Append(wx.ID_ABOUT, "&About MyData")
        self.Bind(wx.EVT_MENU, MyData.OnAbout, id=wx.ID_ABOUT)
        self.menuBar.Append(self.helpMenu, "&Help")
        self.SetMenuBar(self.menuBar)


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
        if hasattr(self.mydataApp, "OnDoSearch"):
            self.parent.Bind(
                wx.EVT_TEXT_ENTER, self.mydataApp.OnDoSearch, self.searchCtrl)
            self.parent.Bind(
                wx.EVT_TEXT, self.mydataApp.OnDoSearch, self.searchCtrl)
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

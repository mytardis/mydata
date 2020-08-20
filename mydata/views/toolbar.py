"""
mydata/views/toolbar.py

MyData's toolbar.
"""
import os
import subprocess
import sys

import wx

from ..dataviewmodels.dataview import DATAVIEW_MODELS
from ..media import MYDATA_ICONS


class MyDataToolbar(object):
    """
    MyData's toolbar.
    """
    def __init__(self, parent):
        self.mydataApp = wx.GetApp()
        self.parent = parent
        self.toolbar = parent.CreateToolBar()
        self.toolbar.SetToolBitmapSize(wx.Size(32, 32))  # sets icon size
        if 'phoenix' in wx.PlatformInfo:
            self.addToolMethod = self.toolbar.AddTool
        else:
            self.addToolMethod = self.toolbar.AddLabelTool

        self.AddOpenFolderTool()

        # Store this as an instance attribute so we can enable/disable it:
        self.testTool = None
        self.AddTestRunTool()

        # Store this as an instance attribute so we can enable/disable it:
        self.uploadTool = None
        self.AddUploadTool()

        # Store this as an instance attribute so we can enable/disable it:
        self.stopTool = None
        self.AddStopTool()

        self.cleanupTool = None
        self.AddCleanupTool()

        # Store this as an instance attribute so we can check whether the
        # Settings dialog was opened by clicking on the toolbar icon:
        self.settingsTool = None
        self.AddSettingsTool()

        self.AddMyTardisTool()
        self.AddAboutTool()
        self.AddHelpTool()

        self.toolbar.AddStretchableSpace()

        self.AddSearchControl()
        self.toolbar.Realize()

    def AddOpenFolderTool(self):
        """
        Add open folder tool
        """
        openIcon = MYDATA_ICONS.GetNewIcon("folder")
        openTool = self.addToolMethod(wx.ID_ANY, "Open folder", openIcon, shortHelp="Open folder")
        self.parent.Bind(wx.EVT_MENU, self.OnOpenFolder, openTool)

    def AddTestRunTool(self):
        """
        Add test run tool for starting test run.
        """
        from ..events.start import OnTestRunFromToolbar
        testIcon = MYDATA_ICONS.GetNewIcon("refresh")
        self.testTool = self.addToolMethod(wx.ID_ANY, "Test Run", testIcon, shortHelp="Test Run")
        self.parent.Bind(wx.EVT_TOOL, OnTestRunFromToolbar, self.testTool, self.testTool.GetId())

    def AddUploadTool(self):
        """
        Add upload tool
        """
        from ..events.start import OnScanAndUploadFromToolbar
        uploadIcon = MYDATA_ICONS.GetNewIcon("start")
        self.uploadTool = self.addToolMethod(
            wx.ID_ANY,
            "Scan and Upload",
            uploadIcon,
            shortHelp="Scan and Upload")
        self.parent.Bind(
            wx.EVT_TOOL,
            OnScanAndUploadFromToolbar,
            self.uploadTool,
            self.uploadTool.GetId())

    def AddStopTool(self):
        """
        Add stop tool for stopping scans and uploads.
        """
        from ..events.stop import OnStop
        stopIcon = MYDATA_ICONS.GetNewIcon("stop")
        self.stopTool = self.addToolMethod(
            wx.ID_STOP,
            "Stop",
            stopIcon,
            shortHelp="Stop")
        self.toolbar.EnableTool(self.stopTool.GetId(), False)
        self.parent.Bind(wx.EVT_TOOL, OnStop, self.stopTool, self.stopTool.GetId())

    def AddCleanupTool(self):
        """
        Add Cleanup button to the toolbar
        """
        from ..events.start import OnCleanup
        cleanupIcon = MYDATA_ICONS.GetNewIcon("nuke")
        self.cleanupTool = self.addToolMethod(
            wx.ID_ANY,
            "Cleanup",
            cleanupIcon,
            shortHelp="Cleanup")
        self.toolbar.EnableTool(self.cleanupTool.GetId(), False)
        self.parent.Bind(wx.EVT_TOOL, OnCleanup, self.cleanupTool, self.cleanupTool.GetId())

    def AddSettingsTool(self):
        """
        Add settings tool for opening Settings dialog.
        """
        from ..events.settings import OnSettings
        settingsIcon = MYDATA_ICONS.GetNewIcon("settings")
        self.settingsTool = self.addToolMethod(
            wx.ID_ANY,
            "Settings",
            settingsIcon,
            shortHelp="Settings")
        self.parent.Bind(wx.EVT_TOOL, OnSettings, self.settingsTool)

    def AddMyTardisTool(self):
        """
        Add MyTardis tool for opening MyTardis in a web browser.
        """
        internetIcon = MYDATA_ICONS.GetNewIcon("globe")
        myTardisTool = self.addToolMethod(
            wx.ID_ANY,
            "MyTardis",
            internetIcon,
            shortHelp="MyTardis")
        if hasattr(self.parent, "OnMyTardis"):
            self.parent.Bind(wx.EVT_TOOL, self.parent.OnMyTardis, myTardisTool)

    def AddAboutTool(self):
        """
        Add About tool for opening MyData's About dialog.
        """
        aboutIcon = MYDATA_ICONS.GetNewIcon("information")
        aboutTool = self.addToolMethod(
            wx.ID_ANY,
            "About MyData",
            aboutIcon,
            shortHelp="About MyData")
        self.parent.Bind(wx.EVT_TOOL, self.parent.OnAbout, aboutTool)

    def AddHelpTool(self):
        """
        Add Help tool for opening MyData's online help.
        """
        from ..events.docs import OnHelp
        helpIcon = MYDATA_ICONS.GetNewIcon("guide")
        helpTool = self.addToolMethod(wx.ID_ANY, "Help", helpIcon, shortHelp="MyData User Guide")
        self.parent.Bind(wx.EVT_TOOL, OnHelp, helpTool)

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
        self.toolbar.EnableTool(self.cleanupTool.GetId(), True)

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
        self.toolbar.EnableTool(self.cleanupTool.GetId(), False)

    def OnOpenFolder(self, event):
        """
        Open the selected folder
        """
        event.StopPropagation()
        foldersModel = DATAVIEW_MODELS['folders']
        foldersView = self.parent.dataViews['folders']
        items = foldersView.dataViewControl.GetSelections()
        rows = [foldersModel.GetRow(item) for item in items]
        if len(rows) != 1:
            if len(rows) > 1:
                message = "Please select a single folder."
            else:
                message = "Please select a folder to open."
            dlg = wx.MessageDialog(self.parent, message, "Open Folder", wx.OK)
            dlg.ShowModal()
            return
        row = rows[0]

        folderModel = foldersModel.rowsData[row]
        if not folderModel.isExperimentFilesFolder:
            path = os.path.join(folderModel.location, folderModel.folderName)
        else:
            path = folderModel.location
        if not os.path.exists(path):
            message = "Path doesn't exist: " + path
            dlg = wx.MessageDialog(None, message, "Open Folder", wx.OK)
            dlg.ShowModal()
            return
        if sys.platform == 'darwin':
            def OpenFolder(path):
                """Open folder."""
                subprocess.check_call(['open', '--', path])
        elif sys.platform.startswith('linux'):
            def OpenFolder(path):
                """Open folder."""
                subprocess.check_call(['xdg-open', '--', path])
        else:  # sys.platform.startswith('win')
            def OpenFolder(path):
                """Open folder."""
                subprocess.call(['explorer', path])

        OpenFolder(path)

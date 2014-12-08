import sys
import wx
import wx.aui
import webbrowser
import os
import appdirs
import sqlite3
import traceback
import threading
import argparse

from FoldersView import FoldersView
from FoldersModel import FoldersModel
from FolderModel import FolderModel
from FoldersController import FoldersController

from UsersView import UsersView
from UsersModel import UsersModel
from UserModel import UserModel

from UploadsView import UploadsView
from UploadsModel import UploadsModel
from UploadModel import UploadModel

from UploaderModel import UploaderModel

from LogView import LogView

from SettingsModel import SettingsModel
from SettingsDialog import SettingsDialog

from Exceptions import NoActiveNetworkInterface

import EnhancedStatusBar as ESB

from logger.Logger import logger

from MyDataTaskBarIcon import MyDataTaskBarIcon

# ----------------------------------------------------------------------


class NotebookTabs:
    FOLDERS = 0
    USERS = 1
    UPLOADS = 2


class MyDataFrame(wx.Frame):
    def __init__(self, parent, id, title, style, settingsModel):
        wx.Frame.__init__(self, parent, id, title, style=style)
        self.settingsModel = settingsModel
        self.SetSize(wx.Size(1000, 600))
        self.statusbar = ESB.EnhancedStatusBar(self, -1)
        self.statusbar.SetSize((-1, 28))
        self.statusbar.SetFieldsCount(2)
        self.SetStatusBar(self.statusbar)
        self.statusbar.SetStatusWidths([-1, 60])
        if hasattr(sys, "frozen"):
            sysExecutableDir = os.path.dirname(sys.executable)
            pngNormalPath = os.path.join(sysExecutableDir, "png-normal")
        else:
            myDataModuleDir = os.path.dirname(os.path.realpath(__file__))
            pngNormalPath = os.path.join(myDataModuleDir, "png-normal")
        self.connectedBitmap = \
            wx.Image(os.path.join(pngNormalPath, "icons24x24", "Connect.png"),
                     wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.disconnectedBitmap = \
            wx.Image(os.path.join(pngNormalPath,
                                  "icons24x24", "Disconnect.png"),
                     wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.connected = False
        self.SetConnected(settingsModel.GetMyTardisUrl(), False)

        # FIXME: Arbitrary separation between MyDataApp and MyDataFrame
        # classes.  Make MyDataApp class tiny and move most of its
        # methods to MyDataFrame?

    def SetOnRefreshRunning(self, onRefreshRunning):
        wx.GetApp().SetOnRefreshRunning(onRefreshRunning)

    def SetStatusMessage(self, msg):
        self.statusbarText = wx.StaticText(self.statusbar, -1, msg)
        self.statusbar.AddWidget(self.statusbarText, pos=0)

    def SetConnected(self, myTardisUrl, connected):

        if self.connected == connected:
            return

        self.myTardisUrl = myTardisUrl
        self.connected = connected

        if self.myTardisUrl != self.settingsModel.GetMyTardisUrl():
            # This probably came from an old thread which took a while to
            # return a connection error.  While it was attempting to connect,
            # the user may have corrected the MyTardis URL in the Settings
            # dialog.
            return

        self.statusbarConnIcon = wx.StaticBitmap(self.statusbar, wx.ID_ANY)
        if connected:
            self.statusbarConnIcon.SetBitmap(self.connectedBitmap)
            self.SetStatusMessage("Connected to " + myTardisUrl)
        else:
            self.statusbarConnIcon.SetBitmap(self.disconnectedBitmap)
            self.SetStatusMessage("Not connected to " + myTardisUrl)
        self.statusbar.AddWidget(self.statusbarConnIcon, pos=1)


class MyData(wx.App):
    def __init__(self, name):
        self.name = name
        wx.App.__init__(self, redirect=False)

    def OnInit(self):
        appname = "MyData"
        appauthor = "Monash University"
        appdirPath = appdirs.user_data_dir(appname, appauthor)
        logger.debug("appdirPath: " + appdirPath)
        if not os.path.exists(appdirPath):
            os.makedirs(appdirPath)

        # Most of the SQLite stuff was designed for the case where MyData
        # is stateful, i.e. it remembers which folders were dragged into
        # the application during its previous runs.  However currently
        # development is focusing on the case where MyData scans a data
        # directory every time it runs and doesn't "remember" any
        # dragged and dropped folders from previous runs.  So the SQLite
        # functionality is being phased out (at least for Settings), and
        # being replaced with a ConfigParser-readable plain-text file.

        self.sqlitedb = os.path.join(appdirPath, appname + '.db')
        logger.debug("self.sqlitedb: " + self.sqlitedb)

        # mydata.cfg stores settings in INI format, readable by ConfigParser
        self.mydataConfigPath = os.path.join(appdirPath, appname + '.cfg')
        logger.debug("self.mydataConfigPath: " + self.mydataConfigPath)

        self.settingsModel = SettingsModel(self.mydataConfigPath,
                                           self.sqlitedb)
        parser = argparse.ArgumentParser()
        parser.add_argument("-b", "--background", action="store_true",
                            help="run non-interactively")
        # parser.add_argument("--loglevel", help="set logging verbosity")
        args = parser.parse_args()
        self.settingsModel.SetBackgroundMode(args.background)

        try:
            self.uploaderModel = UploaderModel(self.settingsModel)

            def requestStagingAccess(uploaderModel):
                uploaderModel.RequestStagingAccess()

            thread = threading.Thread(target=requestStagingAccess,
                                      args=(self.uploaderModel,))
            thread.start()
        except NoActiveNetworkInterface, e:
            message = str(e)
            dlg = wx.MessageDialog(None, message, "MyData",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
        except:
            logger.error(traceback.format_exc())

        try:
            conn = sqlite3.connect(self.sqlitedb)

            with conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS users (" +
                          "id integer primary key," +
                          "username text," +
                          "name text," +
                          "email text)")
                c.execute("CREATE TABLE IF NOT EXISTS folders (" +
                          "id integer primary key," +
                          "folder text," +
                          "location text," +
                          "folder_type text," +
                          "owner_id integer)")
                # Currently we are not saving uploads to disk,
                # i.e. they are only per session, so maybe we don't need this:
                c.execute("CREATE TABLE IF NOT EXISTS uploads (" +
                          "id integer primary key," +
                          "folder_id integer," +
                          "datafile_index integer," +
                          "progress integer)")
                c.execute("DELETE FROM uploads")
        except:
            logger.error(traceback.format_exc())

        self.usersModel = UsersModel(self.sqlitedb, self.settingsModel)
        self.foldersModel = FoldersModel(self.sqlitedb, self.usersModel,
                                         self.settingsModel)
        self.usersModel.SetFoldersModel(self.foldersModel)
        self.uploadsModel = UploadsModel()

        self.frame = MyDataFrame(None, -1, self.name,
                                 style=wx.DEFAULT_FRAME_STYLE,
                                 settingsModel=self.settingsModel)

        self.onRefreshRunning = False
        self.ShutdownForRefreshCompleteEvent, \
            self.EVT_SHUTDOWN_COMPLETE = wx.lib.newevent.NewEvent()
        self.frame.Bind(self.EVT_SHUTDOWN_COMPLETE,
                        self.OnRefresh)
        self.SettingsValidationForRefreshCompleteEvent, \
            self.EVT_SETTINGS_VALIDATION_COMPLETE = wx.lib.newevent.NewEvent()
        self.frame.Bind(self.EVT_SETTINGS_VALIDATION_COMPLETE,
                        self.OnRefresh)

        self.tbIcon = MyDataTaskBarIcon(self.frame)

        wx.EVT_TASKBAR_LEFT_UP(self.tbIcon, self.OnTaskBarLeftClick)

        self.frame.Bind(wx.EVT_CLOSE, self.OnCloseFrame)
        self.frame.Bind(wx.EVT_ICONIZE, self.OnMinimizeFrame)

        img = wx.Image("favicon.ico", wx.BITMAP_TYPE_ANY)
        bmp = wx.BitmapFromImage(img)
        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(bmp)
        self.frame.SetIcon(icon)

        self.panel = wx.Panel(self.frame)

        self.foldersUsersNotebook = \
            wx.aui.AuiNotebook(self.panel,
                               style=wx.aui.AUI_NB_TOP
                               | wx.aui.AUI_NB_SCROLL_BUTTONS)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGING,
                  self.OnNotebookPageChanging, self.foldersUsersNotebook)

        self.foldersView = FoldersView(self.frame,
                                       foldersModel=self.foldersModel)

        self.foldersUsersNotebook.AddPage(self.foldersView, "Folders")
        self.foldersController = \
            FoldersController(self.frame,
                              self.foldersModel,
                              self.foldersView,
                              self.usersModel,
                              self.uploadsModel,
                              self.settingsModel)

        self.usersView = UsersView(self.frame, usersModel=self.usersModel)
        self.foldersUsersNotebook.AddPage(self.usersView, "Users")

        self.uploadsView = \
            UploadsView(self.frame, uploadsModel=self.uploadsModel,
                        foldersController=self.foldersController)
        self.foldersUsersNotebook.AddPage(self.uploadsView, "Uploads")

        self.logView = LogView(self.frame)
        self.foldersUsersNotebook.AddPage(self.logView, "Log")

        self.CreateToolbar()

        sizer = wx.BoxSizer()
        sizer.Add(self.foldersUsersNotebook, 1, flag=wx.EXPAND)
        self.panel.SetSizer(sizer)

        sizer = wx.BoxSizer()
        sizer.Add(self.panel, 1, flag=wx.EXPAND)
        self.frame.SetSizer(sizer)

        self.foldersUsersNotebook.SendSizeEvent()

        self.panel.SetFocus()

        self.SetTopWindow(self.frame)

        self.frame.Show(True)

        event = None
        if self.settingsModel.RequiredFieldIsBlank():
            self.OnSettings(event)
        else:
            self.frame.SetTitle("MyData - " +
                                self.settingsModel.GetInstrumentName())
            if self.settingsModel.RunningInBackgroundMode():
                self.frame.Iconize()
                self.OnRefresh(event)
            else:
                self.OnSettings(event)

        return True

    def OnTaskBarLeftClick(self, evt):
        self.tbIcon.PopupMenu(self.tbIcon.CreatePopupMenu())

    def OnCloseFrame(self, event):
        """
        Don't actually close it, just iconize it.
        """
        self.frame.Show()  # See: http://trac.wxwidgets.org/ticket/10426
        self.frame.Hide()

    def OnMinimizeFrame(self, event):
        """
        When minimizing, hide the frame so it "minimizes to tray"
        """
        if event.Iconized():
            self.frame.Show()  # See: http://trac.wxwidgets.org/ticket/10426
            self.frame.Hide()
            # self.tbIcon.ShowBalloon("MyData",
            #                         "Click the MyData icon " +
            #                         "to access its menu.")

    def CreateToolbar(self):
        """
        Create a toolbar.
        """

        if hasattr(sys, "frozen"):
            sysExecutableDir = os.path.dirname(sys.executable)
            pngNormalPath = os.path.join(sysExecutableDir, "png-normal")
            pngHotPath = os.path.join(sysExecutableDir, "png-hot")
        else:
            myDataModuleDir = os.path.dirname(os.path.realpath(__file__))
            pngNormalPath = os.path.join(myDataModuleDir, "png-normal")
            pngHotPath = os.path.join(myDataModuleDir, "png-hot")

        self.toolbar = self.frame.CreateToolBar()
        self.toolbar.SetToolBitmapSize(wx.Size(24, 24))  # sets icon size

        openIcon = wx.Image(os.path.join(pngNormalPath,
                                         "icons24x24", "Open folder.png"),
                            wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        openTool = self.toolbar.AddSimpleTool(wx.ID_ANY, openIcon, "Open",
                                              "Open folder")
        self.Bind(wx.EVT_MENU, self.OnOpen, openTool)

        self.toolbar.AddSeparator()

        undoIcon = wx.Image(os.path.join(pngNormalPath,
                                         "icons24x24", "Undo.png"),
                            wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.undoTool = self.toolbar.AddSimpleTool(wx.ID_UNDO, undoIcon,
                                                   "Undo", "")
        self.toolbar.EnableTool(wx.ID_UNDO, False)
        # self.Bind(wx.EVT_TOOL, self.onUndo, self.undoTool)

        redoIcon = wx.Image(os.path.join(pngNormalPath,
                                         "icons24x24", "Redo.png"),
                            wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.redoTool = self.toolbar.AddSimpleTool(wx.ID_REDO, redoIcon,
                                                   "Redo", "")
        self.toolbar.EnableTool(wx.ID_REDO, False)
        # self.Bind(wx.EVT_TOOL, self.onRedo, self.redoTool)

        self.toolbar.AddSeparator()

        refreshIcon = wx.Image(os.path.join(pngNormalPath,
                                            "icons24x24", "Refresh.png"),
                               wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.refreshTool = self.toolbar.AddSimpleTool(wx.ID_REFRESH,
                                                      refreshIcon,
                                                      "Refresh", "")
        self.toolbar.EnableTool(wx.ID_REFRESH, True)
        self.Bind(wx.EVT_TOOL, self.OnRefresh, self.refreshTool)

        self.toolbar.AddSeparator()

        settingsIcon = wx.Image(os.path.join(pngHotPath,
                                             "icons24x24", "Settings.png"),
                                wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.settingsTool = self.toolbar.AddSimpleTool(wx.ID_ANY, settingsIcon,
                                                       "Settings", "")
        self.Bind(wx.EVT_TOOL, self.OnSettings, self.settingsTool)

        self.toolbar.AddSeparator()

        internetIcon = \
            wx.Image(os.path.join(pngNormalPath,
                                  "icons24x24", "Internet explorer.png"),
                     wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.myTardisTool = self.toolbar.AddSimpleTool(wx.ID_ANY, internetIcon,
                                                       "MyTardis", "")
        self.Bind(wx.EVT_TOOL, self.OnMyTardis, self.myTardisTool)

        self.toolbar.AddSeparator()

        aboutIcon = wx.Image(os.path.join(pngHotPath,
                                          "icons24x24", "About.png"),
                             wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.aboutTool = self.toolbar.AddSimpleTool(wx.ID_ANY, aboutIcon,
                                                    "About MyData", "")
        self.Bind(wx.EVT_TOOL, self.OnAbout, self.aboutTool)

        self.toolbar.AddSeparator()

        helpIcon = wx.Image(os.path.join(pngHotPath,
                                         "icons24x24", "Help.png"),
                            wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.helpTool = self.toolbar.AddSimpleTool(wx.ID_ANY, helpIcon,
                                                   "MyData User Guide", "")
        self.Bind(wx.EVT_TOOL, self.OnHelp, self.helpTool)

        self.toolbar.AddStretchableSpace()
        self.searchCtrl = wx.SearchCtrl(self.toolbar, size=wx.Size(200, -1),
                                        style=wx.TE_PROCESS_ENTER)
        self.searchCtrl.ShowSearchButton(True)
        self.searchCtrl.ShowCancelButton(True)

        self.Bind(wx.EVT_TEXT_ENTER, self.OnDoSearch, self.searchCtrl)
        self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.searchCtrl)

        self.toolbar.AddControl(self.searchCtrl)

        # This basically shows the toolbar
        self.toolbar.Realize()

        # self.SetCallFilterEvent(True)

    # def OnSearchButton(self,event):
        # pass

    # def OnSearchCancel(self,event):
        # pass

    def OnDoSearch(self, event):
        if self.foldersUsersNotebook.GetSelection() == NotebookTabs.FOLDERS:
            self.foldersModel.Filter(event.GetString())
        else:
            self.usersModel.Filter(event.GetString())

    def SetOnRefreshRunning(self, onRefreshRunning):
        self.onRefreshRunning = onRefreshRunning

    def OnRefresh(self, event):
        settingsValidationAlreadyDone = False
        shutdownForRefreshAlreadyComplete = False
        if hasattr(event, "settingsValidationAlreadyDone") and \
                event.settingsValidationAlreadyDone:
            settingsValidationAlreadyDone = True
            shutdownForRefreshAlreadyComplete = True
        elif hasattr(event, "shutdownSuccessful") and event.shutdownSuccessful:
            shutdownForRefreshAlreadyComplete = True
        if self.onRefreshRunning and not shutdownForRefreshAlreadyComplete:
            self.frame.SetStatusMessage(
                "Shutting down existing data scan and upload processes...")

            def shutDownDataScansAndUploads():
                try:
                    wx.CallAfter(wx.BeginBusyCursor)
                    self.foldersController.ShutDownUploadThreads()
                    wx.PostEvent(
                        self.frame,
                        self.ShutdownForRefreshCompleteEvent(
                            shutdownSuccessful=True))
                    wx.CallAfter(wx.EndBusyCursor)
                except:
                    logger.debug(traceback.format_exc())
                    message = "An error occurred while trying to shut down " \
                        "the existing data-scan-and-upload process in order " \
                        "to start another one.\n\n" \
                        "See the Log tab for details of the error."
                    logger.error(message)

                    def showDialog():
                        dlg = wx.MessageDialog(None, message, "MyData",
                                               wx.OK | wx.ICON_ERROR)
                        dlg.ShowModal()
                    wx.CallAfter(showDialog)
                    return

            thread = threading.Thread(target=shutDownDataScansAndUploads)
            thread.start()
            return

        # Reset the status message to the connection status:
        self.frame.SetConnected(self.settingsModel.GetMyTardisUrl(),
                                False)
        self.foldersController.SetShuttingDown(False)
        self.onRefreshRunning = True

        self.searchCtrl.SetValue("")

        if not settingsValidationAlreadyDone:
            self.frame.SetStatusMessage("Validating settings...")
            self.settingsValidation = None

            def validateSettings():
                try:
                    wx.CallAfter(wx.BeginBusyCursor)
                    if hasattr(self, "uploaderModel") and \
                            self.uploaderModel is not None:
                        activeNetworkInterfaces = \
                            self.uploaderModel.GetActiveNetworkInterfaces()
                        if len(activeNetworkInterfaces) == 0:
                            message = "No active network interfaces." \
                                "\n\n" \
                                "Please ensure that you have an active " \
                                "network interface (e.g. Ethernet or WiFi)."

                            def showDialog():
                                dlg = wx.MessageDialog(None, message, "MyData",
                                                       wx.OK | wx.ICON_ERROR)
                                dlg.ShowModal()
                                wx.EndBusyCursor()
                                self.frame.SetStatusMessage("")
                                self.frame.SetConnected(
                                    self.settingsModel.GetMyTardisUrl(), False)
                            wx.CallAfter(showDialog)
                            return

                    self.settingsValidation = self.settingsModel.Validate()
                    wx.PostEvent(
                        self.frame,
                        self.SettingsValidationForRefreshCompleteEvent(
                            settingsValidationAlreadyDone=True))
                    wx.CallAfter(wx.EndBusyCursor)
                except:
                    logger.debug(traceback.format_exc())
                    return

            thread = threading.Thread(target=validateSettings)
            thread.start()
            return

        if not self.settingsValidation.valid:
            message = self.settingsValidation.message
            logger.error(message)
            dlg = wx.MessageDialog(None, message, "MyData",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            self.OnSettings(event)
            return

        # Set up progress dialog...
        self.progressDialog = \
            wx.ProgressDialog(
                "Scanning folders in " +
                self.settingsModel.GetDataDirectory(), "",
                self.usersModel.GetNumUserFolders(),
                style=wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE | wx.PD_SMOOTH)
        self.numUserFoldersScanned = 0
        self.keepGoing = True

        def incrementProgressDialog():
            self.numUserFoldersScanned = self.numUserFoldersScanned + 1
            message = "Scanned %d of %d folders in %s" % (
                self.numUserFoldersScanned,
                self.usersModel.GetNumUserFolders(),
                self.settingsModel.GetDataDirectory())
            self.keepGoing = \
                self.progressDialog.Update(self.numUserFoldersScanned,
                                           message)

        def scanDataDirs():
            wx.CallAfter(wx.BeginBusyCursor)
            self.usersModel.DeleteAllRows()
            self.foldersModel.DeleteAllRows()
            wx.CallAfter(self.frame.SetStatusMessage,
                         "Scanning data folders...")
            self.usersModel.Refresh(incrementProgressDialog)
            wx.CallAfter(self.progressDialog.Destroy)
            wx.CallAfter(self.frame.SetStatusMessage,
                         "Starting data uploads...")
            self.foldersController.StartDataUploads()
            wx.CallAfter(wx.EndBusyCursor)
        thread = threading.Thread(target=scanDataDirs)
        thread.start()

    def OnOpen(self, event):
        if self.foldersUsersNotebook.GetSelection() == NotebookTabs.FOLDERS:
            self.foldersController.OnOpenFolder(event)

    def OnDelete(self, event):
        if self.foldersUsersNotebook.GetSelection() == NotebookTabs.FOLDERS:
            self.foldersController.OnDeleteFolders(event)
        else:
            self.usersView.OnDeleteUsers(event)

    def OnNotebookPageChanging(self, event):
        if hasattr(self, 'searchCtrl'):
            self.searchCtrl.SetValue("")

    def OnSettings(self, event):
        settingsDialog = SettingsDialog(self.frame, -1, "Settings",
                                        self.settingsModel,
                                        size=wx.Size(400, 400),
                                        style=wx.DEFAULT_DIALOG_STYLE)
        if settingsDialog.ShowModal() == wx.ID_OK:
            myTardisUrlChanged = (self.settingsModel.GetMyTardisUrl() !=
                                  settingsDialog.GetMyTardisUrl())
            if myTardisUrlChanged:
                self.frame.SetConnected(settingsDialog.GetMyTardisUrl(), False)

            self.frame.SetTitle("MyData - " +
                                self.settingsModel.GetInstrumentName())

            def uploadUploaderInfo(uploaderModel, settingsModel):
                try:
                    wx.CallAfter(wx.BeginBusyCursor)
                    if uploaderModel is None:
                        uploaderModel = UploaderModel(settingsModel)
                    uploaderModel.UploadUploaderInfo()
                    wx.CallAfter(self.frame.SetConnected,
                                 self.settingsModel.GetMyTardisUrl(), True)
                except:
                    logger.error(traceback.format_exc())
                    wx.CallAfter(self.frame.SetConnected,
                                 self.settingsModel.GetMyTardisUrl(), False)
                finally:
                    wx.CallAfter(wx.EndBusyCursor)

            if not hasattr(self, "uploaderModel"):
                self.uploaderModel = None
            thread = threading.Thread(target=uploadUploaderInfo,
                                      args=(self.uploaderModel,
                                            self.settingsModel))
            self.frame.SetStatusMessage(
                "Uploading basic info about your PC to MyTardis.")
            thread.start()

            self.OnRefresh(None)

    def OnMyTardis(self, event):
        try:
            import webbrowser
            items = self.foldersView.GetDataViewControl().GetSelections()
            rows = [self.foldersModel.GetRow(item) for item in items]
            if len(rows) == 1:
                folderRecord = self.foldersModel.GetFolderRecord(rows[0])
                if folderRecord.GetDatasetModel() is not None:
                    webbrowser\
                        .open(self.settingsModel.GetMyTardisUrl() + "/" +
                              folderRecord.GetDatasetModel().GetViewUri())
                else:
                    webbrowser.open(self.settingsModel.GetMyTardisUrl())
            else:
                webbrowser.open(self.settingsModel.GetMyTardisUrl())
        except:
            logger.error(traceback.format_exc())

    def OnHelp(self, event):
        new = 2  # Open in a new tab, if possible
        url = "https://github.com/wettenhj/mydata/blob/master/User%20Guide.md"
        webbrowser.open(url, new=new)

    def OnAbout(self, event):
        import CommitDef
        import MyDataVersionNumber
        msg = "MyData is a desktop application" \
              " for uploading data to MyTardis " \
              "(https://github.com/mytardis/mytardis).\n\n" \
              "MyData is being developed at the Monash e-Research Centre " \
              "(Monash University, Australia)\n\n" \
              "MyData is open source (GPL3) software available from " \
              "https://github.com/wettenhj/mydata\n\n" \
              "Version:   " + MyDataVersionNumber.versionNumber + "\n" \
              "Commit:  " + CommitDef.LATEST_COMMIT + "\n"
        dlg = wx.MessageDialog(None, msg, "About MyData",
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()


def main(argv):
    app = MyData("MyData")
    app.MainLoop()

if __name__ == "__main__":
    main(sys.argv)

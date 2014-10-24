import sys
import wx
import wx.aui
import webbrowser
import os

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

from LogView import LogView

from SettingsModel import SettingsModel

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
        self.connected = False
        self.SetConnected(settingsModel.GetMyTardisUrl(), False)

    def SetStatusMsg(self, msg):
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

        if connected:
            # img = wx.ART_TICK_MARK
            bmp = wx.Image('png-normal/icons24x24/Connect.png',
                           wx.BITMAP_TYPE_PNG).ConvertToBitmap()
            self.SetStatusMsg('Connected to ' + myTardisUrl)
        else:
            # img = wx.ART_ERROR
            bmp = wx.Image('png-normal/icons24x24/Disconnect.png',
                           wx.BITMAP_TYPE_PNG).ConvertToBitmap()
            self.SetStatusMsg('Not connected to ' + myTardisUrl)

        # bmp = wx.ArtProvider_GetBitmap(img, wx.ART_TOOLBAR, (16,16))

        self.statusbarConnIcon = wx.StaticBitmap(self.statusbar, -1, bmp)
        # self.statusbarConnIcon.Bind(wx.EVT_LEFT_UP, self.ChangeStatusBarIcon)
        self.statusbar.AddWidget(self.statusbarConnIcon, pos=1)


class MyData(wx.App):
    def __init__(self, name):
        self.name = name
        wx.App.__init__(self, redirect=False)

    def OnInit(self):

        import os
        import appdirs
        appname = "MyData"
        appauthor = "Monash University"
        appdirPath = appdirs.user_data_dir(appname, appauthor)
        if not os.path.exists(appdirPath):
            os.makedirs(appdirPath)
        self.sqlitedb = os.path.join(appdirPath, appname + '.db')

        self.settingsModel = SettingsModel(self.sqlitedb)

        import sqlite3
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

        self.usersModel = UsersModel(self.sqlitedb, self.settingsModel)
        self.foldersModel = FoldersModel(self.sqlitedb, self.usersModel,
                                         self.settingsModel)
        self.usersModel.SetFoldersModel(self.foldersModel)
        self.uploadsModel = UploadsModel(self.sqlitedb)

        self.frame = MyDataFrame(None, -1, self.name,
                                 style=wx.DEFAULT_FRAME_STYLE,
                                 settingsModel=self.settingsModel)

        self.tbIcon = MyDataTaskBarIcon(self.frame)

        wx.EVT_TASKBAR_LEFT_UP(self.tbIcon, self.OnTaskBarLeftClick)

        self.frame.Bind(wx.EVT_CLOSE, self.OnCloseFrame)
        self.frame.Bind(wx.EVT_ICONIZE, self.OnMinimizeFrame)

        # img = wx.Image("icon_048.png", wx.BITMAP_TYPE_ANY)
        img = wx.Image("favicon.ico", wx.BITMAP_TYPE_ANY)
        bmp = wx.BitmapFromImage(img)
        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(bmp)
        self.frame.SetIcon(icon)

        self.panel = wx.Panel(self.frame)

        self.foldersUsersNotebook = \
            wx.aui.AuiNotebook(self.panel,
                               style=wx.aui.AUI_NB_TOP
                               | wx.aui.AUI_NB_TAB_SPLIT
                               | wx.aui.AUI_NB_TAB_MOVE
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

        self.uploadsView = UploadsView(self.frame,
                                       uploadsModel=self.uploadsModel)
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

        wx.CallAfter(self.foldersUsersNotebook.SendSizeEvent)

        self.panel.SetFocus()

        self.SetTopWindow(self.frame)

        self.frame.Show(True)

        event = None
        if self.settingsModel.GetInstrumentName() is None or \
                self.settingsModel.GetInstrumentName() == "":
            self.OnSettings(event)
        elif self.settingsModel.GetInstitutionName() is None or \
                self.settingsModel.GetInstitutionName() == "":
            self.OnSettings(event)
        elif self.settingsModel.GetDataDirectory() is None or \
                self.settingsModel.GetDataDirectory() == "":
            self.OnSettings(event)
        elif self.settingsModel.GetMyTardisUrl() is None or \
                self.settingsModel.GetMyTardisUrl() == "":
            self.OnSettings(event)
        elif self.settingsModel.GetUsername() is None or \
                self.settingsModel.GetUsername() == "":
            self.OnSettings(event)
        elif self.settingsModel.GetApiKey() is None or \
                self.settingsModel.GetApiKey() == "":
            self.OnSettings(event)
        else:
            self.frame.SetTitle("MyData - " +
                                self.settingsModel.GetInstrumentName())
            self.frame.Iconize()
            self.OnRefresh(None)

        return True

    def OnTaskBarLeftClick(self, evt):
        self.tbIcon.PopupMenu(self.tbIcon.CreatePopupMenu())

    def OnCloseFrame(self, event):

        self.frame.Show()  # See: http://trac.wxwidgets.org/ticket/10426
        self.frame.Hide()
        self.tbIcon.ShowBalloon("MyData",
                                "Click the MyData icon to access its menu.")

        # logger.debug("OnCloseFrame: Cleaning up...")
        # self.foldersController.CleanUp()
        # logger.debug("OnCloseFrame: Finished cleaning up...")
        # event.Skip()

    def OnMinimizeFrame(self, event):
        """
        When minimizing, hide the frame so it "minimizes to tray"
        """
        if event.Iconized():
            self.frame.Show()  # See: http://trac.wxwidgets.org/ticket/10426
            self.frame.Hide()
            self.tbIcon.ShowBalloon("MyData",
                                    "Click the MyData icon " +
                                    "to access its menu.")

    def CreateToolbar(self):
        """
        Create a toolbar.
        """

        self.toolbar = self.frame.CreateToolBar()
        self.toolbar.SetToolBitmapSize(wx.Size(24, 24))  # sets icon size

        open_ico = wx.Image('png-normal/icons24x24/Open folder.png',
                            wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        openTool = self.toolbar.AddSimpleTool(wx.ID_ANY, open_ico, "Open",
                                              "Open folder")
        self.Bind(wx.EVT_MENU, self.OnOpen, openTool)

        self.toolbar.AddSeparator()

        undo_ico = wx.Image('png-normal/icons24x24/Undo.png',
                            wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.undoTool = self.toolbar.AddSimpleTool(wx.ID_UNDO, undo_ico,
                                                   "Undo", "")
        self.toolbar.EnableTool(wx.ID_UNDO, False)
        # self.Bind(wx.EVT_TOOL, self.onUndo, self.undoTool)

        redo_ico = wx.Image('png-normal/icons24x24/Redo.png',
                            wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.redoTool = self.toolbar.AddSimpleTool(wx.ID_REDO, redo_ico,
                                                   "Redo", "")
        self.toolbar.EnableTool(wx.ID_REDO, False)
        # self.Bind(wx.EVT_TOOL, self.onRedo, self.redoTool)

        self.toolbar.AddSeparator()

        refresh_ico = wx.Image('png-normal/icons24x24/Refresh.png',
                               wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.refreshTool = self.toolbar.AddSimpleTool(wx.ID_REFRESH,
                                                      refresh_ico,
                                                      "Refresh", "")
        self.toolbar.EnableTool(wx.ID_REFRESH, True)
        self.Bind(wx.EVT_TOOL, self.OnRefresh, self.refreshTool)

        self.toolbar.AddSeparator()

        settings_ico = wx.Image('png-hot/icons24x24/Settings.png',
                                wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.settingsTool = self.toolbar.AddSimpleTool(wx.ID_ANY, settings_ico,
                                                       "Settings", "")
        self.Bind(wx.EVT_TOOL, self.OnSettings, self.settingsTool)

        self.toolbar.AddSeparator()

        internet_ico = wx.Image('png-normal/icons24x24/Internet explorer.png',
                                wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.myTardisTool = self.toolbar.AddSimpleTool(wx.ID_ANY, internet_ico,
                                                       "MyTardis", "")
        self.Bind(wx.EVT_TOOL, self.OnMyTardis, self.myTardisTool)

        self.toolbar.AddSeparator()

        about_ico = wx.Image('png-hot/icons24x24/About.png',
                             wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.aboutTool = self.toolbar.AddSimpleTool(wx.ID_ANY, about_ico,
                                                   "About MyData", "")
        self.Bind(wx.EVT_TOOL, self.OnAbout, self.aboutTool)

        self.toolbar.AddSeparator()

        help_ico = wx.Image('png-hot/icons24x24/Help.png',
                            wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.helpTool = self.toolbar.AddSimpleTool(wx.ID_ANY, help_ico,
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

    def OnRefresh(self, event):

        self.searchCtrl.SetValue("")

        if not os.path.exists(self.settingsModel.GetDataDirectory()):
            message = "The data directory: \"%s\" was not found!"
            logger.error(message)
            dlg = wx.MessageDialog(None, message, "MyData",
                               wx.OK | wx.ICON_ERROR)
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
        self.progressDialog.Destroy()

        # Clear both the users view and the folders view,
        # because when we scan the C:\MyTardisUsers directory,
        # we will repopulate both users and their data sets.
        self.usersModel.DeleteAllRows()
        self.foldersModel.DeleteAllRows()
        self.usersModel.Refresh(incrementProgressDialog)

        # self.foldersModel.Refresh()

        self.foldersController.Refresh()

        self.foldersController.StartDataUploads()

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
        from SettingsDialog import SettingsDialog

        settingsDialog = SettingsDialog(self.frame, -1, "Settings",
                                        size=wx.Size(400, 400),
                                        style=wx.DEFAULT_DIALOG_STYLE)
        settingsDialog.CenterOnParent()
        settingsDialog\
            .SetInstrumentName(self.settingsModel.GetInstrumentName())
        settingsDialog.SetMyTardisUrl(self.settingsModel.GetMyTardisUrl())
        settingsDialog\
            .SetInstitutionName(self.settingsModel.GetInstitutionName())
        settingsDialog.SetDataDirectory(self.settingsModel.GetDataDirectory())
        settingsDialog.SetUsername(self.settingsModel.GetUsername())
        settingsDialog.SetApiKey(self.settingsModel.GetApiKey())

        if settingsDialog.ShowModal() == wx.ID_OK:
            myTardisUrlChanged = (self.settingsModel.GetMyTardisUrl() !=
                                  settingsDialog.GetMyTardisUrl())
            self.settingsModel\
                .SetInstrumentName(settingsDialog.GetInstrumentName())
            self.settingsModel.SetMyTardisUrl(settingsDialog.GetMyTardisUrl())
            self.settingsModel\
                .SetInstitutionName(settingsDialog.GetInstitutionName())
            self.settingsModel\
                .SetDataDirectory(settingsDialog.GetDataDirectory())
            self.settingsModel.SetUsername(settingsDialog.GetUsername())
            self.settingsModel.SetApiKey(settingsDialog.GetApiKey())
            self.settingsModel.Save()
            if myTardisUrlChanged:
                self.frame.SetConnected(settingsDialog.GetMyTardisUrl(), False)

            self.frame.SetTitle("MyData - " +
                                self.settingsModel.GetInstrumentName())
            self.OnRefresh(None)

    def OnMyTardis(self, event):
        import webbrowser
        # webbrowser.open(self.settingsModel.GetMyTardisUrl())
        items = self.foldersView.GetDataViewControl().GetSelections()
        rows = [self.foldersModel.GetRow(item) for item in items]
        if len(rows) == 1:
            folderRecord = self.foldersModel.GetFolderRecord(rows[0])
            if folderRecord.GetDatasetModel() is not None:
                webbrowser.open(self.settingsModel.GetMyTardisUrl() + "/" +
                                folderRecord.GetDatasetModel().GetViewUri())
        else:
            webbrowser.open(self.settingsModel.GetMyTardisUrl())

    def OnHelp(self, event):
        new = 2  # Open in a new tab, if possible
        url = "https://github.com/wettenhj/mydata/blob/master/User%20Guide.md"
        webbrowser.open(url, new=new)

    def OnAbout(self, event):
        import CommitDef
        import MyDataVersionNumber
        msg = "MyData is a desktop application (initially targeting Windows)" \
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

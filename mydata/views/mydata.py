"""
mydata/views/mydata.py

Main window for MyData.
"""
import os
import sys
import threading
import traceback

import wx

from ..constants import APPNAME
from ..logs import logger
from ..media import MYDATA_ICONS
from ..threads.flags import FLAGS
from ..utils import OpenUrl
from ..utils.exceptions import DoesNotExist
from ..events.docs import OnHelp
from ..events.docs import OnWalkthrough
from .dataview import MyDataDataView
from .verifications import VerificationsDataView
from ..dataviewmodels.dataview import DATAVIEW_MODELS
from .log import LogView
from .taskbaricon import MyDataTaskBarIcon
from .toolbar import MyDataToolbar
from ..models.user import UserModel

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

class MyFileDropTarget(wx.FileDropTarget):
    """
    Drag n drop functionality
    """
    # Based on a tutorial from http://zetcode.com/wxpython/draganddrop/
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, mouseX, mouseY, folderName):
        """
        Overridding a wxPython method that provides drag n drop functionality.
        """
        # This method is a wx method. Tell pylint to disable inherent syntax complaints.
        # pylint: disable=no-self-use
        # pylint: disable=unused-argument

        try:
            # Email details dialog here, making sure it grabs the linked user...
            # Then puts all that info in with the upload
            # (through folders/dataviewmodels/models- user records are in there somewhere...)

            assert len(folderName) == 1
            assert os.path.isdir(folderName[0])

            dirAbsPath = str(os.path.abspath(folderName[0]))
            # print dirAbsPath

            dlg = EmailExperimentEntryDialog(self.window, dirAbsPath)
            dlg.ShowModal()

        except AssertionError:
            msg = "Drag n Drop accepts a single [folder].\n"
            dlg = wx.MessageDialog(None, msg)
            dlg.ShowModal()

        return True

class EmailExperimentEntryDialog(wx.Dialog):
    """
    Dialog for entering email for experiments as identifier when using drag-n-drop
    """

    def __init__(self, parent, dirAbsPath):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, "Upload Folder", size=(430, 250))
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.dirAbsPath = dirAbsPath

        intro1 = "The 'dragged_dir' folder will be uploaded to"
        self.intro1 = wx.StaticText(self.panel, label=intro1, pos=(20, 20))
        intro2 = "https://store.erc.monash.edu"
        self.intro2 = wx.StaticText(self.panel, label=intro2, pos=(20, 40))

        intro3 = "Please complete the required fields below:"
        self.intro3 = wx.StaticText(self.panel, label=intro3, pos=(20, 80))

        self.emailLabel = wx.StaticText(self.panel, label="Email", pos=(20, 120))
        self.emailEntry = wx.TextCtrl(self.panel, value="", pos=(110, 120), size=(300, -1))

        #self.experimentLabel = wx.StaticText(self.panel, label="Experiment", pos=(20, 150))
        #self.experimentEntry = wx.TextCtrl(self.panel, value="", pos=(110, 150), size=(300, -1))
        # Add experiment field in a later release

        self.cancelButton = wx.Button(self.panel, label="Cancel", pos=(220, 190))
        self.uploadButton = wx.Button(self.panel, label="Upload", pos=(320, 190))
        self.uploadButton.Bind(wx.EVT_BUTTON, self.OnUpload)
        self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Show()

    def OnCancel(self):
        """
        Behaviour for Cancel Button
        """
        self.EndModal(wx.ID_CANCEL)
        self.Hide()

    def OnUpload(self):
        """
        When upload is clicked, do some sanity checks, then upload
        """
        try:
            email = self.emailEntry.GetValue() # check syntax
            owner = UserModel.GetUserByEmail(email)
            dlg = wx.MessageDialog(self, "Adding to upload queue...")
            dlg.ShowModal()
            # Regular expression validation of email
            # maybe do some exception handling
            DATAVIEW_MODELS['folders'].UploadDraggedFolder(str(self.dirAbsPath), owner)
        except DoesNotExist as doesntExist:
            logger.error(traceback.format_exc())
            dlgError = wx.MessageDialog(self, str(doesntExist))
            dlgError.ShowModal()
        finally:
            self.EndModal(wx.ID_CLOSE)
            self.Hide()

    def OnClose(self, event):
        """
        Behaviour for Close Button
        """
        if event.CanVeto():

            if wx.MessageBox("The upload will not proceed... continue closing?",
                             "Please confirm",
                             wx.ICON_QUESTION | wx.YES_NO) != wx.YES:

                event.Veto()
                return

        self.EndModal(wx.ID_CANCEL)
        self.Hide()  # you may also do:  event.Skip()
                    # since the default event handler does call Destroy(), too


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

        # Let's make this a drag n drop panel
        dropTarget = MyFileDropTarget(self.panel)
        self.panel.SetDropTarget(dropTarget)


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

        helpMenuItemID = wx.NewId()
        helpMenu.Append(helpMenuItemID, "&MyData Help")
        self.Bind(wx.EVT_MENU, OnHelp, id=helpMenuItemID)

        walkthroughMenuItemID = wx.NewId()
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

"""
Represents the Folders tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

import wx
import wx.dataview as dv


class FoldersView(wx.Panel):
    """
    Represents the Folders tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    def __init__(self, parent, foldersModel):
        wx.Panel.__init__(self, parent, -1)

        self.foldersDataViewControl = dv.DataViewCtrl(self,
                                                      style=wx.BORDER_THEME
                                                      | dv.DV_ROW_LINES
                                                      | dv.DV_VERT_RULES
                                                      | dv.DV_MULTIPLE)

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if smallFont.GetPointSize() > 11:
            smallFont.SetPointSize(11)
        self.foldersDataViewControl.SetFont(smallFont)

        self.foldersModel = foldersModel

        self.foldersDataViewControl.AssociateModel(self.foldersModel)

        for col in range(0, self.foldersModel.GetColumnCount()):
            self.foldersDataViewControl\
                .AppendTextColumn(self.foldersModel.GetColumnName(col),
                                  col,
                                  width=self.foldersModel
                                  .GetDefaultColumnWidth(col),
                                  mode=dv.DATAVIEW_CELL_INERT)

        c0 = self.foldersDataViewControl.Columns[0]

        c0.Alignment = wx.ALIGN_RIGHT
        c0.Renderer.Alignment = wx.ALIGN_RIGHT
        c0.MinWidth = 40

        for c in self.foldersDataViewControl.Columns:
            c.Sortable = True
            c.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        c0.Reorderable = False

        # set the Sizer property (same as SetSizer)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.foldersDataViewControl, 1, wx.EXPAND)

        self.openFolderButton = wx.Button(self, label="Open Folder")

        buttonBox = wx.BoxSizer(wx.HORIZONTAL)
        buttonBox.Add(self.openFolderButton, 0, wx.LEFT | wx.RIGHT, 5)
        self.Sizer.Add(buttonBox, 0, wx.TOP | wx.BOTTOM, 5)

        self.lastUsedFolderType = None

    def GetDataViewControl(self):
        return self.foldersDataViewControl

    def GetOpenFolderButton(self):
        return self.openFolderButton

    def DeleteFolderItem(self, folderItem):
        # Remove the selected row(s) from the model. The model will take care
        # of notifying the view (and any other observers) that the change has
        # happened.
        folderId = folderItem.GetID()
        message = "Are you sure you want to remove folder ID #" + \
            str(folderId) + " from the list?"
        confirmationDialog = \
            wx.MessageDialog(None, message, "Confirm Delete",
                             wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        okToDelete = confirmationDialog.ShowModal()
        if okToDelete == wx.ID_OK:
            self.foldersModel.DeleteFolderById(folderId)

    def ShowGroupColumn(self, showOrHide):
        for col in range(0, self.foldersModel.GetColumnCount()):
            column = self.foldersDataViewControl.Columns[col]
            if column.GetTitle() == "Group":
                if showOrHide:
                    width = self.foldersModel.GetDefaultColumnWidth(col)
                else:
                    width = 0
                column.SetWidth(width)


class FoldersPopupMenu(wx.Menu):
    """
    Creates popup menu when user right-clicks on Folders view,
    allowing user to open a data folder in Windows Explorer (Windows)
    or in Finder (Mac OS X).
    """
    def __init__(self, folderItem, openFolderCallback):
        wx.Menu.__init__(self)

        self.folderItem = folderItem
        self.openFolderCallback = openFolderCallback

        self.openFolderMenuItem = wx.MenuItem(self, wx.NewId(), "Open Folder")
        self.AppendItem(self.openFolderMenuItem)
        self.Bind(wx.EVT_MENU, self.OnOpenFolder, self.openFolderMenuItem)

    def OnOpenFolder(self, event):
        """
        Runs the callback which was supplied when initializing the
        FoldersPopupMenu instance.
        """
        self.openFolderCallback(self.folderItem)

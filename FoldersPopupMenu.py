import wx


class FoldersPopupMenu(wx.Menu):
    def __init__(self, folderItem, openFolderCallback, deleteFolderCallback):
        wx.Menu.__init__(self)

        self.folderItem = folderItem
        self.openFolderCallback = openFolderCallback
        self.deleteFolderCallback = deleteFolderCallback

        self.openFolderMenuItem = wx.MenuItem(self, wx.NewId(), "Open Folder")
        self.AppendItem(self.openFolderMenuItem)
        self.Bind(wx.EVT_MENU, self.OnOpenFolder, self.openFolderMenuItem)

        self.deleteFolderMenuItem = wx.MenuItem(self, wx.NewId(),
                                                "Delete Folder")
        self.AppendItem(self.deleteFolderMenuItem)
        self.Bind(wx.EVT_MENU, self.OnDeleteFolder, self.deleteFolderMenuItem)

    def OnDeleteFolder(self, event):
        self.deleteFolderCallback(self.folderItem)

    def OnOpenFolder(self, event):
        self.openFolderCallback(self.folderItem)


import wx
import wx.dataview as dv

from FolderModel import FolderModel

from AddFolderDialog import AddFolderDialog


class FoldersView(wx.Panel):
    def __init__(self, parent, foldersModel):
        wx.Panel.__init__(self, parent, -1)

        # Create a dataview control
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

        # Associate model with the dataview control.  Models can
        # be shared between multiple DataViewCtrls, so this does not
        # assign ownership like many things in wx do.  There is some
        # internal reference counting happening so you don't really
        # need to hold a reference to it either, but we do for this
        # example so we can fiddle with the model from the widget
        # inspector or whatever.
        self.foldersDataViewControl.AssociateModel(self.foldersModel)

        # Now we create some columns.  The second parameter is the
        # column number within the model that the DataViewColumn will
        # fetch the data from.  This means that you can have views
        # using the same model that show different columns of data, or
        # that they can be in a different order than in the model.

        # Technically the column names and widths should be properties
        # of the view, not the model.
        # but it is convenient to keep them in the model, because
        # that's we keep the keys for
        # looking up values in dictionary-like objects.

        for col in range(0, self.foldersModel.GetColumnCount()):
            self.foldersDataViewControl\
                .AppendTextColumn(self.foldersModel.GetColumnName(col),
                                  col,
                                  width=self.foldersModel
                                      .GetDefaultColumnWidth(col),
                                  mode=dv.DATAVIEW_CELL_INERT)

        # There are Prepend methods too, and also convenience methods
        # for other data types but we are only using strings in this
        # example.  You can also create a DataViewColumn object
        # yourself and then just use AppendColumn or PrependColumn.

        c0 = self.foldersDataViewControl.Columns[0]

        # The DataViewColumn object is returned from the Append and
        # Prepend methods, and we can modify some of it's properties
        # like this.
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

        # Bind some events so we can see what the DVC sends us
        self.Bind(dv.EVT_DATAVIEW_ITEM_EDITING_DONE, self.OnEditingDone,
                  self.foldersDataViewControl)
        self.Bind(dv.EVT_DATAVIEW_ITEM_VALUE_CHANGED, self.OnValueChanged,
                  self.foldersDataViewControl)

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

    def OnEditingDone(self, evt):
        pass

    def OnValueChanged(self, evt):
        pass

    def ShowGroupColumn(self, showOrHide):
        for col in range(0, self.foldersModel.GetColumnCount()):
            column = self.foldersDataViewControl.Columns[col]
            if column.GetTitle() == "Group":
                if showOrHide:
                    width = self.foldersModel.GetDefaultColumnWidth(col)
                else:
                    width = 0
                column.SetWidth(width)

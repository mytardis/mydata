
import wx
import wx.dataview as dv

from UsersModel import UsersModel
from UserModel import UserModel


class UsersView(wx.Panel):
    def __init__(self, parent, usersModel):
        wx.Panel.__init__(self, parent, -1)

        # Create a dataview control
        self.usersDataViewControl = dv.DataViewCtrl(self,
                                                    style=wx.BORDER_THEME
                                                    | dv.DV_ROW_LINES
                                                    | dv.DV_VERT_RULES
                                                    | dv.DV_MULTIPLE)

        self.usersModel = usersModel

        # ...and associate it with the dataview control.  Models can
        # be shared between multiple DataViewCtrls, so this does not
        # assign ownership like many things in wx do.  There is some
        # internal reference counting happening so you don't really
        # need to hold a reference to it either, but we do for this
        # example so we can fiddle with the model from the widget
        # inspector or whatever.
        self.usersDataViewControl.AssociateModel(self.usersModel)

        # Now we create some columns.  The second parameter is the
        # column number within the model that the DataViewColumn will
        # fetch the data from.  This means that you can have views
        # using the same model that show different columns of data, or
        # that they can be in a different order than in the model.

        for col in range(1, self.usersModel.GetColumnCount()):
            self.usersDataViewControl\
                .AppendTextColumn(self.usersModel.GetColumnName(col), col,
                                  width=self.usersModel
                                  .GetDefaultColumnWidth(col),
                                  mode=dv.DATAVIEW_CELL_INERT)

        # The DataViewColumn object is returned from the Append and
        # Prepend methods, and we can modify some of it's properties
        # like this.
        c0 = self.usersDataViewControl.PrependTextColumn("Id", 0, width=40)
        c0.Alignment = wx.ALIGN_RIGHT
        c0.Renderer.Alignment = wx.ALIGN_RIGHT
        c0.MinWidth = 40

        # Through the magic of Python we can also access the columns
        # as a list via the Columns property.  Here we'll mark them
        # all as sortable and reorderable.
        for c in self.usersDataViewControl.Columns:
            c.Sortable = True
            c.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        c0.Reorderable = False

        # set the Sizer property (same as SetSizer)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.usersDataViewControl, 1, wx.EXPAND)

        # Bind some events so we can see what the DVC sends us
        self.Bind(dv.EVT_DATAVIEW_ITEM_EDITING_DONE, self.OnEditingDone,
                  self.usersDataViewControl)
        self.Bind(dv.EVT_DATAVIEW_ITEM_VALUE_CHANGED, self.OnValueChanged,
                  self.usersDataViewControl)

    def OnDeleteUsers(self, evt):
        # Remove the selected row(s) from the model. The model will take care
        # of notifying the view (and any other observers) that the change has
        # happened.
        items = self.usersDataViewControl.GetSelections()
        rows = [self.usersModel.GetRow(item) for item in items]
        if len(rows) > 1:
            message = "Are you sure you want to remove the selected users?"
        elif len(rows) == 1:
            message = "Are you sure you want to remove user \"" + \
                self.usersModel.GetValueForRowColname(rows[0], "Name") + "\" ?"
        else:
            dlg = wx.MessageDialog(None, "Please select a user to delete.",
                                   "Delete User(s)", wx.OK)
            dlg.ShowModal()
            return
        confirmationDialog = \
            wx.MessageDialog(None, message, "Confirm Delete",
                             wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        okToDelete = confirmationDialog.ShowModal()
        if okToDelete == wx.ID_OK:
            self.usersModel.DeleteRows(rows)

    def OnAddUser(self, evt):
        from AddUserDialog import AddUserDialog

        addUserDialog = \
            AddUserDialog(self, -1, "Add User", size=(350, 200),
                          style=wx.DEFAULT_DIALOG_STYLE)
        addUserDialog.CenterOnParent()

        if addUserDialog.ShowModal() == wx.ID_OK:
            if self.usersModel.Contains(addUserDialog.GetName(),
                                        addUserDialog.GetEmail()):
                message = "This user has already been added."
                dlg = wx.MessageDialog(None, message, "Add User",
                                       wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                return
            dataViewId = self.usersModel.GetMaxDataViewId() + 1
            userRecord = \
                UserModel(dataViewId=dataViewId,
                          username=addUserDialog.GetUsername(),
                          name=addUserDialog.GetName(),
                          email=addUserDialog.GetEmail())
            self.usersModel.AddRow(userRecord)

    def OnEditingDone(self, evt):
        pass

    def OnValueChanged(self, evt):
        pass

    def GetUsersModel(self):
        return self.usersModel

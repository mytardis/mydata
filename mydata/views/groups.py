import wx
import wx.dataview as dv

from models.group import GroupModel
from dataviewmodels.groups import GroupsModel


class GroupsView(wx.Panel):
    def __init__(self, parent, groupsModel):
        wx.Panel.__init__(self, parent, -1)

        # Create a dataview control
        self.groupsDataViewControl = dv.DataViewCtrl(self,
                                                     style=wx.BORDER_THEME
                                                     | dv.DV_ROW_LINES
                                                     | dv.DV_VERT_RULES
                                                     | dv.DV_MULTIPLE)

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if smallFont.GetPointSize() > 11:
            smallFont.SetPointSize(11)
        self.groupsDataViewControl.SetFont(smallFont)

        self.groupsModel = groupsModel

        # ...and associate it with the dataview control.  Models can
        # be shared between multiple DataViewCtrls, so this does not
        # assign ownership like many things in wx do.  There is some
        # internal reference counting happening so you don't really
        # need to hold a reference to it either, but we do for this
        # example so we can fiddle with the model from the widget
        # inspector or whatever.
        self.groupsDataViewControl.AssociateModel(self.groupsModel)

        # Now we create some columns.  The second parameter is the
        # column number within the model that the DataViewColumn will
        # fetch the data from.  This means that you can have views
        # using the same model that show different columns of data, or
        # that they can be in a different order than in the model.

        for col in range(1, self.groupsModel.GetColumnCount()):
            self.groupsDataViewControl\
                .AppendTextColumn(self.groupsModel.GetColumnName(col), col,
                                  width=self.groupsModel
                                  .GetDefaultColumnWidth(col),
                                  mode=dv.DATAVIEW_CELL_INERT)

        # The DataViewColumn object is returned from the Append and
        # Prepend methods, and we can modify some of it's properties
        # like this.
        c0 = self.groupsDataViewControl.PrependTextColumn("Id", 0, width=40)
        c0.Alignment = wx.ALIGN_RIGHT
        c0.Renderer.Alignment = wx.ALIGN_RIGHT
        c0.MinWidth = 40

        # Through the magic of Python we can also access the columns
        # as a list via the Columns property.  Here we'll mark them
        # all as sortable and reorderable.
        for c in self.groupsDataViewControl.Columns:
            c.Sortable = True
            c.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        c0.Reorderable = False

        # set the Sizer property (same as SetSizer)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.groupsDataViewControl, 1, wx.EXPAND)

        # Bind some events so we can see what the DVC sends us
        self.Bind(dv.EVT_DATAVIEW_ITEM_EDITING_DONE, self.OnEditingDone,
                  self.groupsDataViewControl)
        self.Bind(dv.EVT_DATAVIEW_ITEM_VALUE_CHANGED, self.OnValueChanged,
                  self.groupsDataViewControl)

    def OnEditingDone(self, evt):
        pass

    def OnValueChanged(self, evt):
        pass

    def GetGroupsModel(self):
        return self.groupsModel

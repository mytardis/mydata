"""
Represents the Groups tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

import wx
import wx.dataview as dv


class GroupsView(wx.Panel):
    """
    Represents the Groups tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
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

        self.groupsDataViewControl.AssociateModel(self.groupsModel)

        for col in range(1, self.groupsModel.GetColumnCount()):
            self.groupsDataViewControl\
                .AppendTextColumn(self.groupsModel.GetColumnName(col), col,
                                  width=self.groupsModel
                                  .GetDefaultColumnWidth(col),
                                  mode=dv.DATAVIEW_CELL_INERT)

        c0 = self.groupsDataViewControl.PrependTextColumn("Id", 0, width=40)
        c0.Alignment = wx.ALIGN_RIGHT
        c0.Renderer.Alignment = wx.ALIGN_RIGHT
        c0.MinWidth = 40

        for c in self.groupsDataViewControl.Columns:
            c.Sortable = True
            c.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        c0.Reorderable = False

        # set the Sizer property (same as SetSizer)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.groupsDataViewControl, 1, wx.EXPAND)

    def GetGroupsModel(self):
        """
        Returns the GroupsModel instance associated with the view.
        """
        return self.groupsModel

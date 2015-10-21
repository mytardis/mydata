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
    # pylint: disable=too-few-public-methods
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

        firstColumn = \
            self.groupsDataViewControl.PrependTextColumn("Id", 0, width=40)
        firstColumn.Alignment = wx.ALIGN_RIGHT
        firstColumn.Renderer.Alignment = wx.ALIGN_RIGHT
        firstColumn.MinWidth = 40

        for col in self.groupsDataViewControl.Columns:
            col.Sortable = True
            col.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        firstColumn.Reorderable = False

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.groupsDataViewControl, 1, wx.EXPAND)

    def GetGroupsModel(self):
        """
        Returns the GroupsModel instance associated with the view.
        """
        return self.groupsModel

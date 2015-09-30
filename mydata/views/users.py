"""
Represents the Users tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

import wx
import wx.dataview as dv


class UsersView(wx.Panel):
    """
    Represents the Users tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    def __init__(self, parent, usersModel):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.usersDataViewControl = dv.DataViewCtrl(self,
                                                    style=wx.BORDER_THEME
                                                    | dv.DV_ROW_LINES
                                                    | dv.DV_VERT_RULES
                                                    | dv.DV_MULTIPLE)

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if smallFont.GetPointSize() > 11:
            smallFont.SetPointSize(11)
        self.usersDataViewControl.SetFont(smallFont)

        self.usersModel = usersModel

        self.usersDataViewControl.AssociateModel(self.usersModel)

        for col in range(1, self.usersModel.GetColumnCount()):
            self.usersDataViewControl\
                .AppendTextColumn(self.usersModel.GetColumnName(col), col,
                                  width=self.usersModel
                                  .GetDefaultColumnWidth(col),
                                  mode=dv.DATAVIEW_CELL_INERT)

        firstColumn = \
            self.usersDataViewControl.PrependTextColumn("Id", 0, width=40)
        firstColumn.Alignment = wx.ALIGN_RIGHT
        firstColumn.Renderer.Alignment = wx.ALIGN_RIGHT
        firstColumn.MinWidth = 40

        for col in self.usersDataViewControl.Columns:
            col.Sortable = True
            col.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        firstColumn.Reorderable = False

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.usersDataViewControl, 1, wx.EXPAND)

    def GetUsersModel(self):
        """
        Returns the UsersModel instance associated with the view.
        """
        return self.usersModel

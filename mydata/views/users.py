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

        c0 = self.usersDataViewControl.PrependTextColumn("Id", 0, width=40)
        c0.Alignment = wx.ALIGN_RIGHT
        c0.Renderer.Alignment = wx.ALIGN_RIGHT
        c0.MinWidth = 40

        for c in self.usersDataViewControl.Columns:
            c.Sortable = True
            c.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        c0.Reorderable = False

        # set the Sizer property (same as SetSizer)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.usersDataViewControl, 1, wx.EXPAND)

    def GetUsersModel(self):
        """
        Returns the UsersModel instance associated with the view.
        """
        return self.usersModel

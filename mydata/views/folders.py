"""
Represents the Folders tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

# pylint: disable=missing-docstring

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

        firstColumn = self.foldersDataViewControl.Columns[0]
        firstColumn.Alignment = wx.ALIGN_RIGHT
        firstColumn.Renderer.Alignment = wx.ALIGN_RIGHT
        firstColumn.MinWidth = 40

        for col in self.foldersDataViewControl.Columns:
            col.Sortable = True
            col.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        firstColumn.Reorderable = False

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.foldersDataViewControl, 1, wx.EXPAND)

    def GetDataViewControl(self):
        return self.foldersDataViewControl

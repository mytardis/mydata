"""
The MyDataDataView class is used to render tabular views for the
various tabs in MyData's main window:

  Folders, Users, Groups, Tasks, Verifications, Uploads
"""
import wx
import wx.dataview as dv

from ..dataviewmodels.dataview import ColumnRenderer


class MyDataDataView(wx.Panel):
    """
    Used to render tabular views for the various tabs in MyData's
    main window:

      Folders, Users, Groups, Tasks, Verifications, Uploads
    """
    def __init__(self, parent, dataViewModel):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        # Create a dataview control
        self.dataViewControl = dv.DataViewCtrl(
            self, style=wx.BORDER_THEME | dv.DV_ROW_LINES | dv.DV_VERT_RULES
            | dv.DV_MULTIPLE)

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if smallFont.GetPointSize() > 11:
            smallFont.SetPointSize(11)
        self.dataViewControl.SetFont(smallFont)

        self.dataViewControl.AssociateModel(dataViewModel)

        for col in range(0, dataViewModel.GetColumnCount()):
            renderer = dataViewModel.GetColumnRenderer(col)
            if renderer == ColumnRenderer.TEXT:
                self.dataViewControl.AppendTextColumn(
                    dataViewModel.GetColumnName(col), col,
                    width=dataViewModel.GetDefaultColumnWidth(col),
                    mode=dv.DATAVIEW_CELL_INERT)
            elif renderer == ColumnRenderer.BITMAP:
                column = self.dataViewControl.AppendBitmapColumn(
                    dataViewModel.GetColumnName(col), col,
                    width=dataViewModel.GetDefaultColumnWidth(col),
                    mode=dv.DATAVIEW_CELL_INERT)
                column.Alignment = wx.ALIGN_CENTER
                column.Renderer.Alignment = wx.ALIGN_CENTER
            elif renderer == ColumnRenderer.PROGRESS:
                self.dataViewControl.AppendProgressColumn(
                    dataViewModel.GetColumnName(col), col,
                    width=dataViewModel.GetDefaultColumnWidth(col),
                    mode=dv.DATAVIEW_CELL_INERT,
                    flags=dv.DATAVIEW_COL_RESIZABLE)

        firstColumn = self.dataViewControl.Columns[0]
        firstColumn.Alignment = wx.ALIGN_RIGHT
        firstColumn.Renderer.Alignment = wx.ALIGN_RIGHT
        firstColumn.MinWidth = 40

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.dataViewControl, 1, wx.EXPAND)

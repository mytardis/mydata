"""
Represents the Uploads tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

# pylint: disable=fixme
# pylint: disable=missing-docstring

import wx
import wx.dataview as dv

from mydata.dataviewmodels.uploads import ColumnType
from mydata.utils import BeginBusyCursorIfRequired


class UploadsView(wx.Panel):
    """
    Represents the Uploads tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, parent, uploadsModel, foldersController):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        self.uploadsDataViewControl = dv.DataViewCtrl(self,
                                                      style=wx.BORDER_THEME
                                                      | dv.DV_ROW_LINES
                                                      | dv.DV_VERT_RULES
                                                      | dv.DV_MULTIPLE)

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if smallFont.GetPointSize() > 11:
            smallFont.SetPointSize(11)
        self.uploadsDataViewControl.SetFont(smallFont)

        self.uploadsModel = uploadsModel
        self.foldersController = foldersController

        self.uploadsDataViewControl.AssociateModel(self.uploadsModel)

        for col in range(0, self.uploadsModel.GetColumnCount()):
            if self.uploadsModel.columnTypes[col] == ColumnType.TEXT:
                column = self.uploadsDataViewControl\
                    .AppendTextColumn(self.uploadsModel.GetColumnName(col),
                                      col,
                                      width=self.uploadsModel
                                      .GetDefaultColumnWidth(col),
                                      mode=dv.DATAVIEW_CELL_INERT)
            if self.uploadsModel.columnTypes[col] == ColumnType.BITMAP:
                column = self.uploadsDataViewControl\
                    .AppendBitmapColumn(self.uploadsModel.GetColumnName(col),
                                        col,
                                        width=self.uploadsModel
                                        .GetDefaultColumnWidth(col),
                                        mode=dv.DATAVIEW_CELL_INERT)
                column.Alignment = wx.ALIGN_CENTER
                column.Renderer.Alignment = wx.ALIGN_CENTER
            if self.uploadsModel.columnTypes[col] == ColumnType.PROGRESS:
                self.uploadsDataViewControl\
                    .AppendProgressColumn(self.uploadsModel.GetColumnName(col),
                                          col,
                                          width=self.uploadsModel
                                          .GetDefaultColumnWidth(col),
                                          mode=dv.DATAVIEW_CELL_INERT,
                                          flags=dv.DATAVIEW_COL_RESIZABLE)

        firstColumn = self.uploadsDataViewControl.Columns[0]
        firstColumn.Alignment = wx.ALIGN_RIGHT
        firstColumn.Renderer.Alignment = wx.ALIGN_RIGHT
        firstColumn.MinWidth = 40

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.uploadsDataViewControl, 1, wx.EXPAND)

    def OnCancelRemainingUploads(self, event):
        wx.CallAfter(BeginBusyCursorIfRequired)
        wx.PostEvent(
            self.foldersController.notifyWindow,
            self.foldersController.shutdownUploadsEvent(
                canceled=True))
        if event:
            event.Skip()

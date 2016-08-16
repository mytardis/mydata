"""
Represents the Uploads tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

# pylint: disable=fixme
# pylint: disable=missing-docstring

import traceback
import wx
import wx.dataview as dv

from mydata.dataviewmodels.uploads import ColumnType
from mydata.logs import logger


class UploadsView(wx.Panel):
    """
    Represents the Uploads tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
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

        cancelSelectedUploadsButton = \
            wx.Button(self, label="Cancel Selected Upload(s)")
        self.Bind(wx.EVT_BUTTON, self.OnCancelSelectedUploads,
                  cancelSelectedUploadsButton)

        cancelRemainingUploadsButton = \
            wx.Button(self, label="Cancel All Remaining Upload(s)")
        self.Bind(wx.EVT_BUTTON, self.OnCancelRemainingUploads,
                  cancelRemainingUploadsButton)

        btnbox = wx.BoxSizer(wx.HORIZONTAL)
        btnbox.Add(cancelSelectedUploadsButton, 0, wx.LEFT | wx.RIGHT, 5)
        btnbox.Add(cancelRemainingUploadsButton, 0, wx.LEFT | wx.RIGHT, 5)
        self.Sizer.Add(btnbox, 0, wx.TOP | wx.BOTTOM, 5)

    def OnCancelSelectedUploads(self, event):
        """
        Remove the selected row(s) from the model. The model will take
        care of notifying the view (and any other observers) that the
        change has happened.
        """
        # FIXME: Should warn the user if already-completed uploads
        # exist within the selection (in which case their datafiles
        # won't be deleted from the MyTardis server).
        # The OnCancelRemainingUploads method is a bit smarter in
        # terms of only deleting incomplete upload rows from the view.
        # pylint: disable=bare-except
        try:
            items = self.uploadsDataViewControl.GetSelections()
            rows = [self.uploadsModel.GetRow(item) for item in items]
            if len(rows) > 1:
                message = \
                    "Are you sure you want to cancel the selected uploads?" \
                    "\n\n" \
                    "MyData will attempt to resume the uploads next time " \
                    "it runs."
            elif len(rows) == 1:
                pathToUpload = self.uploadsModel.GetUploadModel(rows[0])\
                    .GetRelativePathToUpload()
                message = "Are you sure you want to cancel uploading " + \
                    "\"" + pathToUpload + "\"?" \
                    "\n\n" \
                    "MyData will attempt to resume the uploads next time " \
                    "it runs."
            else:
                dlg = wx.MessageDialog(None,
                                       "Please select an upload to cancel.",
                                       "Cancel Upload(s)", wx.OK)
                dlg.ShowModal()
                return
            confirmationDialog = \
                wx.MessageDialog(None, message, "MyData",
                                 wx.OK | wx.CANCEL | wx.ICON_QUESTION)
            okToDelete = confirmationDialog.ShowModal()
            if okToDelete == wx.ID_OK:
                self.uploadsModel.DeleteRows(rows)
        except:
            logger.error(traceback.format_exc())
        finally:
            event.Skip()

    def OnCancelRemainingUploads(self, event):
        wx.CallAfter(wx.BeginBusyCursor)
        wx.PostEvent(
            self.foldersController.notifyWindow,
            self.foldersController.shutdownUploadsEvent(
                canceled=True))
        if event:
            event.Skip()

    def GetUploadsModel(self):
        """
        Returns the UploadsModel instance associated with the view.
        """
        return self.uploadsModel

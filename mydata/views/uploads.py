import sys
import wx
import wx.dataview as dv
import traceback
import threading

from mydata.dataviewmodels.uploads import UploadsModel
from mydata.dataviewmodels.uploads import ColumnType
from mydata.models.upload import UploadModel

from mydata.logs import logger


class UploadsView(wx.Panel):

    def __init__(self, parent, uploadsModel, foldersController):
        wx.Panel.__init__(self, parent, -1)

        # Create a dataview control
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

        c0 = self.uploadsDataViewControl.Columns[0]
        c0.Alignment = wx.ALIGN_RIGHT
        c0.Renderer.Alignment = wx.ALIGN_RIGHT
        c0.MinWidth = 40

        # set the Sizer property (same as SetSizer)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.uploadsDataViewControl, 1, wx.EXPAND)

        # Add some buttons
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

    def OnCancelSelectedUploads(self, evt):
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
            logger.debug(traceback.format_exc())

    def OnCancelRemainingUploads(self, evt):
        def shutDownUploadThreads():
            try:
                wx.CallAfter(wx.BeginBusyCursor)
                self.foldersController.ShutDownUploadThreads()

                def endBusyCursorIfRequired():
                    try:
                        wx.EndBusyCursor()
                    except wx._core.PyAssertionError, e:
                        if "no matching wxBeginBusyCursor()" \
                                not in str(e):
                            logger.error(str(e))
                            raise
                wx.CallAfter(endBusyCursorIfRequired)
            except:
                logger.error(traceback.format_exc())
        thread = threading.Thread(target=shutDownUploadThreads)
        thread.start()

    def GetUploadsModel(self):
        return self.uploadsModel

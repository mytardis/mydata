
import wx
import wx.dataview as dv

from UploadsModel import UploadsModel
from UploadModel import UploadModel

from logger.Logger import logger
import traceback


class UploadsView(wx.Panel):
    def __init__(self, parent, uploadsModel):
        wx.Panel.__init__(self, parent, -1)

        # Create a dataview control
        self.uploadsDataViewControl = dv.DataViewCtrl(self,
                                                      style=wx.BORDER_THEME
                                                      | dv.DV_ROW_LINES
                                                      | dv.DV_VERT_RULES
                                                      | dv.DV_MULTIPLE)

        self.uploadsModel = uploadsModel

        # ...and associate it with the dataview control.  Models can
        # be shared between multiple DataViewCtrls, so this does not
        # assign ownership like many things in wx do.  There is some
        # internal reference counting happening so you don't really
        # need to hold a reference to it either, but we do for this
        # example so we can fiddle with the model from the widget
        # inspector or whatever.
        self.uploadsDataViewControl.AssociateModel(self.uploadsModel)

        # Now we create some columns.  The second parameter is the
        # column number within the model that the DataViewColumn will
        # fetch the data from.  This means that you can have views
        # using the same model that show different columns of data, or
        # that they can be in a different order than in the model.

        # Technically the column names and widths should be properties
        # of the view, not the model.
        # but it is convenient to keep them in the model, because
        # that's we keep the keys for
        # looking up values in dictionary-like objects.

        from UploadsModel import ColumnType
        for col in range(0, self.uploadsModel.GetColumnCount()):
            if self.uploadsModel.GetColumnType(col) == ColumnType.TEXT:
                column = self.uploadsDataViewControl\
                    .AppendTextColumn(self.uploadsModel.GetColumnName(col),
                                      col,
                                      width=self.uploadsModel
                                          .GetDefaultColumnWidth(col),
                                      mode=dv.DATAVIEW_CELL_INERT)
            if self.uploadsModel.GetColumnType(col) == ColumnType.BITMAP:
                column = self.uploadsDataViewControl\
                    .AppendBitmapColumn(self.uploadsModel.GetColumnName(col),
                                        col,
                                        width=self.uploadsModel
                                            .GetDefaultColumnWidth(col),
                                        mode=dv.DATAVIEW_CELL_INERT)
                column.Alignment = wx.ALIGN_CENTER
                column.Renderer.Alignment = wx.ALIGN_CENTER
            if self.uploadsModel.GetColumnType(col) == ColumnType.PROGRESS:
                column = self.uploadsDataViewControl\
                    .AppendProgressColumn(self.uploadsModel.GetColumnName(col),
                                          col,
                                          width=self.uploadsModel
                                              .GetDefaultColumnWidth(col),
                                          mode=dv.DATAVIEW_CELL_INERT,
                                          flags=dv.DATAVIEW_COL_RESIZABLE)

        # The DataViewColumn object is returned from the Append and
        # Prepend methods, and we can modify some of it's properties
        # like this.
        c0 = self.uploadsDataViewControl.Columns[0]
        c0.Alignment = wx.ALIGN_RIGHT
        c0.Renderer.Alignment = wx.ALIGN_RIGHT
        c0.MinWidth = 40

        # Through the magic of Python we can also access the columns
        # as a list via the Columns property.  Here we'll mark them
        # all as sortable and reorderable.
        for c in self.uploadsDataViewControl.Columns:
            c.Sortable = True
            c.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        c0.Reorderable = False

        # set the Sizer property (same as SetSizer)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.uploadsDataViewControl, 1, wx.EXPAND)

        # Add some buttons
        b3 = wx.Button(self, label="Cancel Upload(s)")
        self.Bind(wx.EVT_BUTTON, self.OnCancelUploads, b3)

        btnbox = wx.BoxSizer(wx.HORIZONTAL)
        btnbox.Add(b3, 0, wx.LEFT | wx.RIGHT, 5)
        self.Sizer.Add(btnbox, 0, wx.TOP | wx.BOTTOM, 5)

    def OnCancelUploads(self, evt):
        try:
            # Remove the selected row(s) from the model. The model will take
            # care of notifying the view (and any other observers) that the
            # change has happened.
            items = self.uploadsDataViewControl.GetSelections()
            rows = [self.uploadsModel.GetRow(item) for item in items]
            if len(rows) > 1:
                message = \
                    "Are you sure you want to cancel the selected uploads?"
            elif len(rows) == 1:
                pathToUpload = self.uploadsModel.GetUploadModel(rows[0])\
                    .GetRelativePathToUpload()
                message = "Are you sure you want to cancel upload \"" + \
                    pathToUpload + "\" ?"
            else:
                dlg = wx.MessageDialog(None,
                                       "Please select an upload to cancel.",
                                       "Cancel Upload(s)", wx.OK)
                dlg.ShowModal()
                return
            confirmationDialog = \
                wx.MessageDialog(None, message, "Confirm Delete",
                                 wx.OK | wx.CANCEL | wx.ICON_QUESTION)
            okToDelete = confirmationDialog.ShowModal()
            if okToDelete == wx.ID_OK:
                self.uploadsModel.DeleteRows(rows)
        except:
            logger.debug(traceback.format_exc())

    def GetUploadsModel(self):
        return self.uploadsModel

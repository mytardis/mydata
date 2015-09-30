"""
Represents the Verifications tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import traceback
import threading
import wx
import wx.dataview as dv

from mydata.dataviewmodels.verifications import ColumnType
from mydata.logs import logger


# pylint: disable=interface-not-implemented
class VerificationsView(wx.Panel):
    """
    Represents the Verifications tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    def __init__(self, parent, verificationsModel, foldersController):
        wx.Panel.__init__(self, parent, -1)

        # Create a dataview control
        self.verificationsDataViewControl = \
            dv.DataViewCtrl(self, style=wx.BORDER_THEME
                            | dv.DV_ROW_LINES
                            | dv.DV_VERT_RULES
                            | dv.DV_MULTIPLE)

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if smallFont.GetPointSize() > 11:
            smallFont.SetPointSize(11)
        self.verificationsDataViewControl.SetFont(smallFont)

        self.verificationsModel = verificationsModel
        self.foldersController = foldersController

        self.verificationsDataViewControl.AssociateModel(
            self.verificationsModel)

        for col in range(0, self.verificationsModel.GetColumnCount()):
            if self.verificationsModel.columnTypes[col] == ColumnType.TEXT:
                column = self.verificationsDataViewControl\
                    .AppendTextColumn(self.verificationsModel
                                      .GetColumnName(col),
                                      col,
                                      width=self.verificationsModel
                                      .GetDefaultColumnWidth(col),
                                      mode=dv.DATAVIEW_CELL_INERT)
            if self.verificationsModel.columnTypes[col] == ColumnType.BITMAP:
                column = self.verificationsDataViewControl\
                    .AppendBitmapColumn(self.verificationsModel
                                        .GetColumnName(col),
                                        col,
                                        width=self.verificationsModel
                                        .GetDefaultColumnWidth(col),
                                        mode=dv.DATAVIEW_CELL_INERT)
                column.Alignment = wx.ALIGN_CENTER
                column.Renderer.Alignment = wx.ALIGN_CENTER
            if self.verificationsModel.columnTypes[col] == ColumnType.PROGRESS:
                self.verificationsDataViewControl\
                    .AppendProgressColumn(self.verificationsModel
                                          .GetColumnName(col),
                                          col,
                                          width=self.verificationsModel
                                          .GetDefaultColumnWidth(col),
                                          mode=dv.DATAVIEW_CELL_INERT,
                                          flags=dv.DATAVIEW_COL_RESIZABLE)

        c0 = self.verificationsDataViewControl.Columns[0]
        c0.Alignment = wx.ALIGN_RIGHT
        c0.Renderer.Alignment = wx.ALIGN_RIGHT
        c0.MinWidth = 40

        # set the Sizer property (same as SetSizer)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.verificationsDataViewControl, 1, wx.EXPAND)

    def OnCancelSelectedVerifications(self, evt):
        """
        Remove the selected row(s) from the model. The model will take
        care of notifying the view (and any other observers) that the
        change has happened.
        """
        # FIXME: Should warn the user if already-completed verifications
        # exist within the selection (in which case their datafiles
        # won't be deleted from the MyTardis server).
        # The OnCancelRemainingVerifications method is a bit smarter in
        # terms of only deleting incomplete verification rows from the view.
        try:
            items = self.verificationsDataViewControl.GetSelections()
            rows = [self.verificationsModel.GetRow(item) for item in items]
            if len(rows) > 1:
                message = \
                    "Are you sure you want to cancel the selected " \
                    "verifications?" \
                    "\n\n" \
                    "MyData will attempt to resume the verifications " \
                    "next time it runs."
            elif len(rows) == 1:
                pathToVerification = \
                    self.verificationsModel.GetVerificationModel(rows[0])\
                        .GetRelativePathToVerification()
                message = "Are you sure you want to cancel verificationing " + \
                    "\"" + pathToVerification + "\"?" \
                    "\n\n" \
                    "MyData will attempt to resume the verifications " \
                    "next time it runs."
            else:
                dlg = wx.MessageDialog(None,
                                       "Please select an verification "
                                       "to cancel.",
                                       "Cancel Verification(s)", wx.OK)
                dlg.ShowModal()
                return
            confirmationDialog = \
                wx.MessageDialog(None, message, "MyData",
                                 wx.OK | wx.CANCEL | wx.ICON_QUESTION)
            okToDelete = confirmationDialog.ShowModal()
            if okToDelete == wx.ID_OK:
                self.verificationsModel.DeleteRows(rows)
        except:
            logger.debug(traceback.format_exc())

    def OnCancelRemainingVerifications(self, evt):
        def shutDownVerificationThreads():
            try:
                wx.CallAfter(wx.BeginBusyCursor)
                self.foldersController.ShutDownVerificationThreads()
                wx.CallAfter(wx.EndBusyCursor)
            except:
                logger.error(traceback.format_exc())
        thread = threading.Thread(target=shutDownVerificationThreads)
        thread.start()

    def GetVerificationsModel(self):
        return self.verificationsModel

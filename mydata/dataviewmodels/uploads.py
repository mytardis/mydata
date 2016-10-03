"""
Represents the Uploads tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

# pylint: disable=missing-docstring
# pylint: disable=wrong-import-position

import threading
import traceback

import wx
if wx.version().startswith("3.0.3.dev"):
    from wx.dataview import DataViewIndexListModel  # pylint: disable=no-name-in-module
else:
    from wx.dataview import PyDataViewIndexListModel as DataViewIndexListModel

from mydata.models.upload import UploadStatus
from mydata.logs import logger
from mydata.media import MYDATA_ICONS


# pylint: disable=too-few-public-methods
class ColumnType(object):
    """
    Enumerated data type.
    """
    TEXT = 0
    BITMAP = 1
    PROGRESS = 2


class UploadsModel(DataViewIndexListModel):
    """
    Represents the Uploads tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
    def __init__(self):
        self.uploadsData = []

        DataViewIndexListModel.__init__(self, len(self.uploadsData))

        self.columnNames = ("Id", "Folder", "Subdirectory", "Filename",
                            "File Size", "Status", "Progress", "Message")
        self.columnKeys = ("dataViewId", "folder", "subdirectory", "filename",
                           "filesize", "status", "progress", "message")
        self.defaultColumnWidths = (40, 170, 170, 200, 75, 55, 100, 300)
        self.columnTypes = (ColumnType.TEXT, ColumnType.TEXT, ColumnType.TEXT,
                            ColumnType.TEXT, ColumnType.TEXT,
                            ColumnType.BITMAP, ColumnType.PROGRESS,
                            ColumnType.TEXT)

        self.maxDataViewId = 0
        self.maxDataViewIdLock = threading.Lock()
        self.completedCount = 0
        self.completedCountLock = threading.Lock()
        self.failedCount = 0
        self.failedCountLock = threading.Lock()

        self.inProgressIcon = MYDATA_ICONS.GetIcon("Refresh", size="16x16")
        self.completedIcon = MYDATA_ICONS.GetIcon("Apply", size="16x16")
        self.failedIcon = MYDATA_ICONS.GetIcon("Delete", size="16x16")

    # All of our columns are strings.  If the model or the renderers
    # in the view are other types then that should be reflected here.
    def GetColumnType(self, col):
        # pylint: disable=arguments-differ
        if col == self.columnNames.index("Status"):
            return "wxBitmap"
        if col == self.columnNames.index("Progress"):
            return "long"
        return "string"

    # This method is called to provide the uploadsData object for a
    # particular row,col
    def GetValueByRow(self, row, col):
        # pylint: disable=arguments-differ
        try:
            if col == self.columnNames.index("Status"):
                icon = wx.NullBitmap
                if self.uploadsData[row].GetStatus() == \
                        UploadStatus.IN_PROGRESS:
                    icon = self.inProgressIcon
                elif self.uploadsData[row].GetStatus() == \
                        UploadStatus.COMPLETED:
                    icon = self.completedIcon
                elif self.uploadsData[row].GetStatus() == \
                        UploadStatus.FAILED:
                    icon = self.failedIcon
                return icon
            columnKey = self.GetColumnKeyName(col)
            if self.GetColumnType(col) == "string":
                return str(self.uploadsData[row].GetValueForKey(columnKey))
            else:
                return self.uploadsData[row].GetValueForKey(columnKey)
        except IndexError:
            # A "list index out of range" exception can be
            # thrown if the row is currently being deleted
            # logger.debug("UploadsModel's GetValueByRow "
            #              "called on missing row.")
            return None

    def GetColumnName(self, col):
        return self.columnNames[col]

    def GetColumnKeyName(self, col):
        return self.columnKeys[col]

    def GetDefaultColumnWidth(self, col):
        return self.defaultColumnWidths[col]

    def GetRowCount(self):
        """
        Report how many rows this model provides data for.
        """
        return len(self.uploadsData)

    def GetColumnCount(self):
        """
        Report how many columns this model provides data for.
        """
        # pylint: disable=arguments-differ
        return len(self.columnNames)

    def GetCount(self):
        """
        Report the number of rows in the model
        """
        # pylint: disable=arguments-differ
        return len(self.uploadsData)

    def GetAttrByRow(self, row, col, attr):
        """
        Called to check if non-standard attributes should be
        used in the cell at (row, col)
        """
        # pylint: disable=arguments-differ
        # pylint: disable=unused-argument
        # pylint: disable=no-self-use
        return False

    # This is called to assist with sorting the data in the view.  The
    # first two args are instances of the DataViewItem class, so we
    # need to convert them to row numbers with the GetRow method.
    # Then it's just a matter of fetching the right values from our
    # data set and comparing them.  The return value is -1, 0, or 1,
    # just like Python's cmp() function.
    def Compare(self, item1, item2, col, ascending):
        # pylint: disable=arguments-differ
        if not ascending:
            item2, item1 = item1, item2
        row1 = self.GetRow(item1)
        row2 = self.GetRow(item2)
        if col == 0:
            return cmp(int(self.GetValueByRow(row1, col)),
                       int(self.GetValueByRow(row2, col)))
        else:
            return cmp(self.GetValueByRow(row1, col),
                       self.GetValueByRow(row2, col))

    def DeleteAllRows(self):
        rowsDeleted = []
        for row in reversed(range(0, self.GetCount())):
            del self.uploadsData[row]
            rowsDeleted.append(row)

        # notify the view(s) using this model that it has been removed
        if threading.current_thread().name == "MainThread":
            self.RowsDeleted(rowsDeleted)
        else:
            wx.CallAfter(self.RowsDeleted, rowsDeleted)

        self.maxDataViewId = 0
        self.completedCount = 0
        self.failedCount = 0

    def GetMaxDataViewId(self):
        return self.maxDataViewId

    def SetMaxDataViewId(self, dataViewId):
        self.maxDataViewIdLock.acquire()
        self.maxDataViewId = dataViewId
        self.maxDataViewIdLock.release()

    def GetUploadModel(self, row):
        return self.uploadsData[row]

    def AddRow(self, uploadModel):
        self.uploadsData.append(uploadModel)
        # Notify views
        if threading.current_thread().name == "MainThread":
            self.RowAppended()
        else:
            wx.CallAfter(self.RowAppended)

        self.SetMaxDataViewId(uploadModel.GetDataViewId())

    def TryRowValueChanged(self, row, col):
        try:
            if row < self.GetCount():
                self.RowValueChanged(row, col)
            else:
                logger.warning("TryRowValueChanged called with "
                               "row=%d, self.GetRowCount()=%d" %
                               (row, self.GetRowCount()))
                self.RowValueChanged(row, col)
        except wx.PyAssertionError:
            logger.warning(traceback.format_exc())

    def TryRowDeleted(self, row):
        # pylint: disable=bare-except
        try:
            if row < self.GetCount():
                self.RowDeleted(row)
            else:
                logger.warning("TryRowDeleted called with "
                               "row=%d, self.GetRowCount()=%d" %
                               (row, self.GetRowCount()))
        except:
            logger.debug(traceback.format_exc())

    def UploadFileSizeUpdated(self, uploadModel):
        if uploadModel.Canceled():
            return
        for row in reversed(range(0, self.GetCount())):
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("File Size")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def UploadProgressUpdated(self, uploadModel):
        if uploadModel.Canceled():
            return
        for row in reversed(range(0, self.GetCount())):
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("Progress")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def StatusUpdated(self, uploadModel):
        if uploadModel.Canceled():
            return
        for row in reversed(range(0, self.GetCount())):
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("Status")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def MessageUpdated(self, uploadModel):
        if uploadModel.Canceled():
            return
        for row in reversed(range(0, self.GetCount())):
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("Message")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def SetStatus(self, uploadModel, status):
        uploadModel.SetStatus(status)
        if status == UploadStatus.COMPLETED:
            self.completedCountLock.acquire()
            try:
                self.completedCount += 1
            finally:
                self.completedCountLock.release()
        elif status == UploadStatus.FAILED:
            self.failedCountLock.acquire()
            try:
                self.failedCount += 1
            finally:
                self.failedCountLock.release()
        self.StatusUpdated(uploadModel)

    def SetMessage(self, uploadModel, message):
        uploadModel.SetMessage(message)
        self.MessageUpdated(uploadModel)

    def GetCompletedCount(self):
        return self.completedCount

    def GetFailedCount(self):
        return self.failedCount

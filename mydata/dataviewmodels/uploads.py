"""
Represents the Uploads tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

# pylint: disable=missing-docstring
# pylint: disable=wrong-import-position

import threading
import traceback
import datetime

import wx
if wx.version().startswith("3.0.3.dev"):
    from wx.dataview import DataViewIndexListModel  # pylint: disable=no-name-in-module
else:
    from wx.dataview import PyDataViewIndexListModel as DataViewIndexListModel

from mydata.models.upload import UploadStatus
from mydata.logs import logger
from mydata.media import MYDATA_ICONS


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
                            "File Size", "Status", "Progress", "Message", "Speed")
        self.columnKeys = ("dataViewId", "folder", "subdirectory", "filename",
                           "filesize", "status", "progress", "message", "speed")
        self.defaultColumnWidths = (40, 170, 170, 200, 75, 55, 100, 200, 100)
        self.columnTypes = (ColumnType.TEXT, ColumnType.TEXT, ColumnType.TEXT,
                            ColumnType.TEXT, ColumnType.TEXT,
                            ColumnType.BITMAP, ColumnType.PROGRESS,
                            ColumnType.TEXT, ColumnType.TEXT)

        self.maxDataViewId = 0
        self.maxDataViewIdLock = threading.Lock()
        self.completedCount = 0
        self.completedSize = 0
        self.completedCountLock = threading.Lock()
        self.failedCount = 0
        self.failedCountLock = threading.Lock()

        self.inProgressIcon = MYDATA_ICONS.GetIcon("Refresh", size="16x16")
        self.completedIcon = MYDATA_ICONS.GetIcon("Apply", size="16x16")
        self.failedIcon = MYDATA_ICONS.GetIcon("Delete", size="16x16")

        self.startTime = None
        self.finishTime = None

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
                elif self.uploadsData[row].GetStatus() in \
                        (UploadStatus.FAILED,
                         UploadStatus.CANCELED):
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

    def DeleteAllRows(self):
        rowsDeleted = []
        for row in reversed(range(0, self.GetCount())):
            del self.uploadsData[row]
            rowsDeleted.append(row)

        # notify the view(s) using this model that it has been removed
        wx.CallAfter(self.RowsDeleted, rowsDeleted)

        self.maxDataViewId = 0
        self.completedCount = 0
        self.completedSize = 0
        self.failedCount = 0

    def CancelRemaining(self):
        rowsToCancel = []
        for row in range(0, self.GetRowCount()):
            if self.uploadsData[row].GetStatus() != UploadStatus.COMPLETED \
                    and \
                    self.uploadsData[row].GetStatus() != UploadStatus.FAILED:
                rowsToCancel.append(row)
        for row in rowsToCancel:
            uploadModel = self.uploadsData[row]
            uploadModel.Cancel()
            self.SetStatus(uploadModel, UploadStatus.CANCELED)
            self.SetMessage(uploadModel, 'Canceled')

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

    def UploadProgressUpdated(self, uploadModel):
        for row in reversed(range(0, self.GetCount())):
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("Progress")
                wx.CallAfter(self.TryRowValueChanged, row, col)
                col = self.columnNames.index("Speed")
                wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def StatusUpdated(self, uploadModel):
        for row in reversed(range(0, self.GetCount())):
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("Status")
                wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def MessageUpdated(self, uploadModel):
        for row in reversed(range(0, self.GetCount())):
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("Message")
                wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def SetStatus(self, uploadModel, status):
        uploadModel.SetStatus(status)
        if status == UploadStatus.COMPLETED:
            self.completedCountLock.acquire()
            try:
                self.completedCount += 1
                self.completedSize += uploadModel.GetFileSize()
                self.finishTime = datetime.datetime.now()
            finally:
                self.completedCountLock.release()
        elif status == UploadStatus.FAILED:
            self.failedCountLock.acquire()
            try:
                self.failedCount += 1
            finally:
                self.failedCountLock.release()
        self.StatusUpdated(uploadModel)

    def SetStartTime(self, startTime):
        self.startTime = startTime

    def GetElapsedTime(self):
        if self.startTime and self.finishTime:
            return self.finishTime - self.startTime
        else:
            return None

    def SetMessage(self, uploadModel, message):
        uploadModel.SetMessage(message)
        self.MessageUpdated(uploadModel)

    def GetCompletedCount(self):
        return self.completedCount

    def GetCompletedSize(self):
        return self.completedSize

    def GetFailedCount(self):
        return self.failedCount

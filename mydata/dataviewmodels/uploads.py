"""
Represents the Uploads tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import threading
import datetime

import wx

from ..models.upload import UploadStatus
from ..media import MYDATA_ICONS
from .dataview import MyDataDataViewModel
from .dataview import ColumnRenderer


class UploadsModel(MyDataDataViewModel):
    """
    Represents the Uploads tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
    # pylint: disable=arguments-differ
    def __init__(self):
        super(UploadsModel, self).__init__()

        self.columnNames = ["Id", "Folder", "Subdirectory", "Filename",
                            "File Size", "Status", "Progress", "Message",
                            "Speed"]
        self.columnKeys = ["dataViewId", "folder", "subdirectory", "filename",
                           "filesizeString", "status", "progress", "message",
                           "speed"]
        self.defaultColumnWidths = [40, 170, 170, 200, 75, 55, 100, 200, 100]

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

    def GetColumnType(self, col):
        """
        All of our columns are strings.  If the model or the renderers
        in the view are other types then that should be reflected here.
        """
        if col == self.columnNames.index("Status"):
            return "wxBitmap"
        if col == self.columnNames.index("Progress"):
            return "long"
        return "string"

    def GetValueByRow(self, row, col):
        """
        This method is called to provide the rowsData object for a
        particular row,col
        """
        try:
            if col == self.columnNames.index("Status"):
                icon = wx.NullBitmap
                if self.rowsData[row].status == UploadStatus.IN_PROGRESS:
                    icon = self.inProgressIcon
                elif self.rowsData[row].status == UploadStatus.COMPLETED:
                    icon = self.completedIcon
                elif self.rowsData[row].status in \
                        (UploadStatus.FAILED, UploadStatus.CANCELED):
                    icon = self.failedIcon
                return icon
            columnKey = self.GetColumnKeyName(col)
            if self.GetColumnType(col) == "string":
                return str(self.rowsData[row].GetValueForKey(columnKey))
            else:
                return self.rowsData[row].GetValueForKey(columnKey)
        except IndexError:
            # A "list index out of range" exception can be
            # thrown if the row is currently being deleted
            return None

    def DeleteAllRows(self):
        """
        Delete all rows
        """
        super(UploadsModel, self).DeleteAllRows()
        self.completedCount = 0
        self.completedSize = 0
        self.failedCount = 0

    def CancelRemaining(self):
        """
        Cancel remaining
        """
        rowsCanceled = []
        for row in range(0, self.GetRowCount()):
            uploadModel = self.rowsData[row]
            if uploadModel.status != UploadStatus.COMPLETED and \
                    uploadModel.status != UploadStatus.FAILED:
                uploadModel.Cancel()
                rowsCanceled.append(row)

        for row in rowsCanceled:
            uploadModel = self.rowsData[row]
            self.SetStatus(uploadModel, UploadStatus.CANCELED)
            self.SetMessage(uploadModel, 'Canceled')

    def UploadProgressUpdated(self, uploadModel):
        """
        Notify views that upload progress has been updated
        """
        for row in reversed(range(0, self.GetCount())):
            if self.rowsData[row] == uploadModel:
                col = self.columnNames.index("Progress")
                wx.CallAfter(self.TryRowValueChanged, row, col)
                col = self.columnNames.index("Speed")
                wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def StatusUpdated(self, uploadModel):
        """
        Notify views that upload status has been updated
        """
        for row in reversed(range(0, self.GetCount())):
            if self.rowsData[row] == uploadModel:
                col = self.columnNames.index("Status")
                wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def MessageUpdated(self, uploadModel):
        """
        Notify views that upload message has been updated
        """
        for row in reversed(range(0, self.GetCount())):
            if self.rowsData[row] == uploadModel:
                col = self.columnNames.index("Message")
                wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def SetStatus(self, uploadModel, status):
        """
        Update upload status for one UploadModel instance
        """
        uploadModel.status = status
        if status == UploadStatus.COMPLETED:
            self.completedCountLock.acquire()
            try:
                self.completedCount += 1
                self.completedSize += uploadModel.fileSize
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
        """
        Set overall start time for uploads
        """
        self.startTime = startTime

    def GetElapsedTime(self):
        """
        Get overall elapsed time for uploads
        """
        if self.startTime and self.finishTime:
            return self.finishTime - self.startTime
        else:
            return None

    def SetMessage(self, uploadModel, message):
        """
        Update upload message for one UploadModel instance
        """
        uploadModel.message = message
        self.MessageUpdated(uploadModel)

    def GetCompletedCount(self):
        """
        Return the number of completed uploads
        """
        return self.completedCount

    def GetCompletedSize(self):
        """
        Return the total size of the completed uploads
        """
        return self.completedSize

    def GetFailedCount(self):
        """
        Return the number of failed uploads
        """
        return self.failedCount

    def GetColumnRenderer(self, col):
        """
        Return the renderer to be used for the specified dataview column
        """
        if col == 5:
            return ColumnRenderer.BITMAP,
        elif col == 6:
            return ColumnRenderer.PROGRESS,
        else:
            return ColumnRenderer.TEXT

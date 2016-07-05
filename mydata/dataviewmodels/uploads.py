"""
Represents the Uploads tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

# pylint: disable=missing-docstring

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

        # Unfiltered uploads data:
        self.uud = self.uploadsData
        # Filtered uploads data:
        self.fud = list()
        self.filtered = False
        self.searchString = ""

        self.columnNames = ("Id", "Folder", "Subdirectory", "Filename",
                            "File Size", "Status", "Progress", "Message")
        self.columnKeys = ("dataViewId", "folder", "subdirectory", "filename",
                           "filesize", "status", "progress", "message")
        self.defaultColumnWidths = (40, 170, 170, 200, 75, 55, 100, 300)
        self.columnTypes = (ColumnType.TEXT, ColumnType.TEXT, ColumnType.TEXT,
                            ColumnType.TEXT, ColumnType.TEXT,
                            ColumnType.BITMAP, ColumnType.PROGRESS,
                            ColumnType.TEXT)

        # This is the largest ID value which has been used in this model.
        # It may no longer exist, i.e. if we delete the row with the
        # largest ID, we don't decrement the maximum ID.
        self.maxDataViewId = 0

        self.inProgressIcon = MYDATA_ICONS.GetIcon("Refresh", size="16x16")
        self.completedIcon = MYDATA_ICONS.GetIcon("Apply", size="16x16")
        self.failedIcon = MYDATA_ICONS.GetIcon("Delete", size="16x16")

    def Filter(self, searchString):
        """
        Only show uploads method query string.
        """
        # pylint: disable=too-many-branches
        self.searchString = searchString
        query = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.uud = list(self.uploadsData)

        for row in reversed(range(0, self.GetRowCount())):
            upload = self.uploadsData[row]
            if query not in upload.GetFilename().lower():
                self.fud.append(upload)
                del self.uploadsData[row]
                # Notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            fud = self.fud[filteredRow]  # fud = filtered uploads data
            if query in fud.GetFilename().lower():
                # Model doesn't care about currently sorted column.
                # Always use ID.
                row = 0
                col = 0
                ascending = True
                while row < self.GetRowCount() and \
                        self.CompareUploadRecords(self.uploadsData[row],
                                                  fud, col, ascending) < 0:
                    row = row + 1

                if row == self.GetRowCount():
                    self.uploadsData.append(fud)
                    # Notify the view that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowAppended()
                    else:
                        wx.CallAfter(self.RowAppended)
                else:
                    self.uploadsData.insert(row, fud)
                    # Notify the view that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowInserted(row)
                    else:
                        wx.CallAfter(self.RowInserted, row)
                del self.fud[filteredRow]
                if self.GetFilteredRowCount() == 0:
                    self.filtered = False

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

    def GetValuesForColname(self, colname):
        values = []
        col = -1
        for col in range(0, self.GetColumnCount()):
            if self.GetColumnName(col) == colname:
                break
        if col == self.GetColumnCount():
            return None

        for row in range(0, self.GetRowCount()):
            values.append(self.GetValueByRow(row, col))
        return values

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

    def GetUnfilteredRowCount(self):
        """
        Report how many rows this model provides data for.
        """
        return len(self.uud)

    def GetFilteredRowCount(self):
        return len(self.fud)

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

    # Unlike the previous Compare method, in this case,
    # the upload records don't need
    # to be visible in the current (possibly filtered) data view.
    def CompareUploadRecords(self, uploadRecord1, uploadRecord2, col,
                             ascending):
        if not ascending:
            uploadRecord2, uploadRecord1 = uploadRecord1, uploadRecord2
        if col == 0:
            return cmp(int(uploadRecord1.GetDataViewId()),
                       int(uploadRecord2.GetDataViewId()))
        else:
            return cmp(uploadRecord1.GetValueForKey(self.columnKeys[col]),
                       uploadRecord2.GetValueForKey(self.columnKeys[col]))

    def DeleteRows(self, rows):
        # Ensure that we save the largest ID used so far:
        self.GetMaxDataViewId()

        # make a copy since we'll be sorting(mutating) the list
        rows = list(rows)
        # use reverse order so the indexes don't change as we remove items
        rows.sort(reverse=True)

        for row in rows:
            logger.debug("DeleteRows: Canceling upload: " +
                         self.uploadsData[row].GetRelativePathToUpload())
            self.uploadsData[row].Cancel()
            del self.uploadsData[row]
            del self.uud[row]

        # Notify the view(s) that these rows have been removed
        if threading.current_thread().name == "MainThread":
            self.RowsDeleted(rows)
        else:
            wx.CallAfter(self.RowsDeleted, rows)

    def DeleteUpload(self, folderModel, dataFileIndex):
        # Ensure that we save the largest ID used so far:
        self.GetMaxDataViewId()

        for row in range(0, self.GetRowCount()):
            if self.uploadsData[row].GetFolderModel() == folderModel and \
                    self.uploadsData[row].GetDataFileIndex() == dataFileIndex:
                del self.uploadsData[row]
                del self.uud[row]
                # Notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.TryRowDeleted(row)
                else:
                    wx.CallAfter(self.TryRowDeleted, row)
                return

    def Contains(self, filename):
        for row in range(0, self.GetCount()):
            if self.uploadsData[row].GetFilename().strip() == filename:
                return True
        return False

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

        self.uud = list()
        self.fud = list()
        self.filtered = False
        self.searchString = ""
        self.maxDataViewId = 0

    def GetMaxDataViewIdFromExistingRows(self):
        maxDataViewId = 0
        for row in range(0, self.GetCount()):
            if self.uploadsData[row].GetDataViewId() > maxDataViewId:
                maxDataViewId = self.uploadsData[row].GetDataViewId()
        return maxDataViewId

    def GetMaxDataViewId(self):
        if self.GetMaxDataViewIdFromExistingRows() > self.maxDataViewId:
            self.maxDataViewId = self.GetMaxDataViewIdFromExistingRows()
        return self.maxDataViewId

    def GetUploadModel(self, row):
        return self.uploadsData[row]

    def AddRow(self, value):
        self.uploadsData.append(value)
        # Notify views
        if threading.current_thread().name == "MainThread":
            self.RowAppended()
        else:
            wx.CallAfter(self.RowAppended)

        self.uud = self.uploadsData
        self.fud = list()
        self.Filter(self.searchString)

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
        for row in range(0, self.GetCount()):
            # Uploads could be in the process of being canceled:
            if row >= self.GetCount():
                break
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("File Size")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)

    def UploadProgressUpdated(self, uploadModel):
        if uploadModel.Canceled():
            return
        for row in range(0, self.GetCount()):
            # Uploads could be in the process of being canceled:
            if row >= self.GetCount():
                break
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("Progress")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)

    def UploadStatusUpdated(self, uploadModel):
        if uploadModel.Canceled():
            return
        for row in range(0, self.GetCount()):
            # Uploads could be in the process of being canceled:
            if row >= self.GetCount():
                break
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("Status")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)

    def UploadMessageUpdated(self, uploadModel):
        if uploadModel.Canceled():
            return
        for row in range(0, self.GetCount()):
            # Uploads could be in the process of being canceled:
            if row >= self.GetCount():
                break
            if self.uploadsData[row] == uploadModel:
                col = self.columnNames.index("Message")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)

    def CancelRemaining(self):
        app = wx.GetApp()
        if threading.current_thread().name == "MainThread":
            app.EnableTestAndUploadToolbarButtons()
        else:
            wx.CallAfter(app.EnableTestAndUploadToolbarButtons)
        rowsToDelete = []
        for row in range(0, self.GetRowCount()):
            if self.uploadsData[row].GetStatus() != UploadStatus.COMPLETED \
                    and \
                    self.uploadsData[row].GetStatus() != UploadStatus.FAILED:
                rowsToDelete.append(row)

        # Ensure that we save the largest ID used so far:
        self.GetMaxDataViewId()
        for row in reversed(rowsToDelete):
            self.uploadsData[row].Cancel()
            del self.uploadsData[row]
            del self.uud[row]
        if threading.current_thread().name == "MainThread":
            self.RowsDeleted(rowsToDelete)
        else:
            wx.CallAfter(self.RowsDeleted, rowsToDelete)

        self.fud = list()
        self.filtered = False
        self.searchString = ""
        self.maxDataViewId = 0

    def GetCompletedCount(self):
        completedCount = 0
        for row in range(0, self.GetRowCount()):
            if self.uploadsData[row].GetStatus() == UploadStatus.COMPLETED:
                completedCount += 1
        return completedCount

    def GetFailedCount(self):
        failedCount = 0
        for row in range(0, self.GetRowCount()):
            if self.uploadsData[row].GetStatus() == UploadStatus.FAILED:
                failedCount += 1
        return failedCount

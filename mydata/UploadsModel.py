import wx.dataview
import threading
import traceback

from UploadModel import UploadModel
from UploadModel import UploadStatus
from logger.Logger import logger

# This model class provides the data to the view when it is asked for.
# Since it is a list-only model (no hierachical data) then it is able
# to be referenced by row rather than by item object, so in this way
# it is easier to comprehend and use than other model types.  In this
# example we also provide a Compare function to assist with sorting of
# items in our model.  Notice that the data items in the data model
# object don't ever change position due to a sort or column
# reordering.  The view manages all of that and maps view rows and
# columns to the model's rows and columns as needed.
#
# Our data is stored in a list of UploadModel objects.


class ColumnType:
    TEXT = 0
    BITMAP = 1
    PROGRESS = 2


class UploadsModel(wx.dataview.PyDataViewIndexListModel):

    def __init__(self):

        self.uploadsData = []

        wx.dataview.PyDataViewIndexListModel.__init__(self,
                                                      len(self.uploadsData))

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

        self.inProgressIcon = wx.Image('media/Aha-Soft/png-normal/icons16x16/Refresh.png',
                                       wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.completedIcon = wx.Image('media/Aha-Soft/png-normal/icons16x16/Apply.png',
                                      wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.failedIcon = wx.Image('media/Aha-Soft/png-normal/icons16x16/Delete.png',
                                   wx.BITMAP_TYPE_PNG).ConvertToBitmap()

    def Filter(self, searchString):
        self.searchString = searchString
        q = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.uud = list(self.uploadsData)

        for row in reversed(range(0, self.GetRowCount())):
            ud = self.uploadsData[row]
            if q not in ud.GetFilename().lower():
                self.fud.append(ud)
                del self.uploadsData[row]
                # Notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            fud = self.fud[filteredRow]
            if q in fud.GetFilename().lower():
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
        if col == self.columnNames.index("Status"):
            return "wxBitmap"
        if col == self.columnNames.index("Progress"):
            return "long"
        return "string"

    # This method is called to provide the uploadsData object for a
    # particular row,col
    def GetValueByRow(self, row, col):
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

    # Report how many rows this model provides data for.
    def GetRowCount(self):
        return len(self.uploadsData)

    # Report how many rows this model provides data for.
    def GetUnfilteredRowCount(self):
        return len(self.uud)

    # Report how many rows this model provides data for.
    def GetFilteredRowCount(self):
        return len(self.fud)

    # Report how many columns this model provides data for.
    def GetColumnCount(self):
        return len(self.columnNames)

    # Report the number of rows in the model
    def GetCount(self):
        return len(self.uploadsData)

    # Called to check if non-standard attributes should be used in the
    # cell at (row, col)
    def GetAttrByRow(self, row, col, attr):
        return False

    # This is called to assist with sorting the data in the view.  The
    # first two args are instances of the DataViewItem class, so we
    # need to convert them to row numbers with the GetRow method.
    # Then it's just a matter of fetching the right values from our
    # data set and comparing them.  The return value is -1, 0, or 1,
    # just like Python's cmp() function.
    def Compare(self, item1, item2, col, ascending):
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
            if self.uploadsData[row].GetFilename().strip() == name:
                return True
        return False

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
        except:
            logger.debug(traceback.format_exc())

    def TryRowDeleted(self, row):
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

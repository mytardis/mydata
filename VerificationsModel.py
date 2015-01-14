import wx.dataview
import os
import threading

from VerificationModel import VerificationModel
from VerificationModel import VerificationStatus
from UploadsModel import ColumnType
from logger.Logger import logger


class VerificationsModel(wx.dataview.PyDataViewIndexListModel):
    def __init__(self):

        self.foldersModel = None

        self.verificationsData = list()

        wx.dataview.PyDataViewIndexListModel.__init__(self,
                                                      len(self.verificationsData))

        # Unfiltered verifications data:
        self.uvd = self.verificationsData
        # Filtered verifications data:
        self.fvd = list()
        self.filtered = False
        self.searchString = ""

        self.columnNames = ("Id", "Folder", "Subdirectory", "Filename", "Message")
        self.columnKeys = ("dataViewId", "folder", "subdirectory", "filename", "message")
        self.defaultColumnWidths = (40, 170, 170, 200, 500)
        self.columnTypes = (ColumnType.TEXT, ColumnType.TEXT, ColumnType.TEXT,
                            ColumnType.TEXT, ColumnType.TEXT)

        # This is the largest ID value which has been used in this model.
        # It may no longer exist, i.e. if we delete the row with the
        # largest ID, we don't decrement the maximum ID.
        self.maxDataViewId = 0

        # self.inProgressIcon = wx.Image('png-normal/icons16x16/Refresh.png',
                                       # wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        # self.completedIcon = wx.Image('png-normal/icons16x16/Apply.png',
                                      # wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        # self.failedIcon = wx.Image('png-normal/icons16x16/Delete.png',
                                   # wx.BITMAP_TYPE_PNG).ConvertToBitmap()


    def SetFoldersModel(self, foldersModel):
        self.foldersModel = foldersModel

    def Filter(self, searchString):
        self.searchString = searchString
        q = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.uvd = list(self.verificationsData)

        for row in reversed(range(0, self.GetRowCount())):
            vd = self.verificationsData[row]
            if q not in vd.GetFilename().lower() and \
                    q not in vd.GetFolder().lower() and \
                    q not in vd.GetSubdirectory().lower() and \
                    q not in vd.GetMessage().lower():
                self.fvd.append(vd)
                del self.verificationsData[row]
                # Notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            fvd = self.fvd[filteredRow]
            if q in fvd.GetFilename().lower() or \
                    q in fvd.GetFolder().lower() or \
                    q in fvd.GetSubdirectory().lower() or \
                    q in fvd.GetMessage().lower():
                # Model doesn't care about currently sorted column.
                # Always use ID.
                row = 0
                col = 0
                ascending = True
                while row < self.GetRowCount() and \
                        self.CompareVerificationRecords(self.verificationsData[row],
                                                        fvd, col, ascending) < 0:
                    row = row + 1

                if row == self.GetRowCount():
                    self.verificationsData.append(fvd)
                    # Notify the view that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowAppended()
                    else:
                        wx.CallAfter(self.RowAppended)
                else:
                    self.verificationsData.insert(row, fvd)
                    # Notify the view that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowInserted(row)
                    else:
                        wx.CallAfter(self.RowInserted, row)
                del self.fvd[filteredRow]
                if self.GetFilteredRowCount() == 0:
                    self.filtered = False

    # All of our columns are strings.  If the model or the renderers
    # in the view are other types then that should be reflected here.
    def GetColumnType(self, col):
        return "string"

    # This method is called to provide the verificationsData object for a
    # particular row, col
    def GetValueByRow(self, row, col):
        columnKey = self.GetColumnKeyName(col)
        return str(self.verificationsData[row].GetValueForKey(columnKey))

    # This method is called to provide the verificationsData object for a
    # particular row, colname
    def GetValueForRowColname(self, row, colname):
        for col in range(0, self.GetColumnCount()):
            if self.GetColumnName(col) == colname:
                return self.GetValueByRow(row, col)
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
        return len(self.verificationsData)

    # Report how many rows this model provides data for.
    def GetUnfilteredRowCount(self):
        return len(self.uvd)

    # Report how many rows this model provides data for.
    def GetFilteredRowCount(self):
        return len(self.fvd)

    # Report how many columns this model provides data for.
    def GetColumnCount(self):
        return len(self.columnNames)

    # Report the number of rows in the model
    def GetCount(self):
        return len(self.verificationsData)

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
        # Swap sort order?
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

    # Unlike the previous Compare method, in this case, the verification records
    # don't need to be visible in the current (possibly filtered) data view.
    def CompareVerificationRecords(self, verificationRecord1, verificationRecord2, col, ascending):
        # Swap sort order?
        if not ascending:
            verificationRecord2, verificationRecord1 = verificationRecord1, verificationRecord2
        if col == 0:
            return cmp(int(verificationRecord1.GetDataViewId()),
                       int(verificationRecord2.GetDataViewId()))
        else:
            return cmp(verificationRecord1.GetValueForKey(self.columnKeys[col]),
                       verificationRecord2.GetValueForKey(self.columnKeys[col]))

    def DeleteRows(self, rows):
        # Ensure that we save the largest ID used so far:
        self.GetMaxDataViewId()

        # make a copy since we'll be sorting(mutating) the list
        rows = list(rows)
        # use reverse order so the indexes don't change as we remove items
        rows.sort(reverse=True)

        for row in rows:
            del self.verificationsData[row]
            del self.uvd[row]

        # Notify the view(s) using this model that it has been removed
        if threading.current_thread().name == "MainThread":
            self.RowsDeleted(rows)
        else:
            wx.CallAfter(self.RowsDeleted, rows)

    def DeleteAllRows(self):
        rowsDeleted = []
        for row in reversed(range(0, self.GetCount())):
            del self.verificationsData[row]
            rowsDeleted.append(row)

        # notify the view(s) using this model that it has been removed
        if threading.current_thread().name == "MainThread":
            self.RowsDeleted(rowsDeleted)
        else:
            wx.CallAfter(self.RowsDeleted, rowsDeleted)

        self.uvd = list()
        self.fvd = list()
        self.filtered = False
        self.searchString = ""
        self.maxDataViewId = 0

    def GetMaxDataViewIdFromExistingRows(self):
        maxDataViewId = 0
        for row in range(0, self.GetCount()):
            if self.verificationsData[row].GetDataViewId() > maxDataViewId:
                maxDataViewId = self.verificationsData[row].GetDataViewId()
        return maxDataViewId

    def GetMaxDataViewId(self):
        if self.GetMaxDataViewIdFromExistingRows() > self.maxDataViewId:
            self.maxDataViewId = self.GetMaxDataViewIdFromExistingRows()
        return self.maxDataViewId

    def AddRow(self, value):
        self.Filter("")
        self.verificationsData.append(value)
        # Notify views
        if threading.current_thread().name == "MainThread":
            self.RowAppended()
        else:
            wx.CallAfter(self.RowAppended)

        self.uvd = self.verificationsData
        self.fvd = list()
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

    def VerificationMessageUpdated(self, verificationModel):
        for row in range(0, self.GetCount()):
            if row >= self.GetCount():
                break
            if self.verificationsData[row] == verificationModel:
                col = self.columnNames.index("Message")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)

    def GetFoundVerifiedCount(self):
        foundVerifiedCount = 0
        for row in range(0, self.GetRowCount()):
            if self.verificationsData[row].GetStatus() == \
                    VerificationStatus.FOUND_VERIFIED:
                foundVerifiedCount += 1
        return foundVerifiedCount

    def GetNotFoundCount(self):
        notFoundCount = 0
        for row in range(0, self.GetRowCount()):
            if self.verificationsData[row].GetStatus() == \
                    VerificationStatus.NOT_FOUND:
                notFoundCount += 1
        return notFoundCount

    def GetFoundUnverifiedFullSizeCount(self):
        foundUnverifiedFullSizeCount = 0
        for row in range(0, self.GetRowCount()):
            if self.verificationsData[row].GetStatus() == \
                    VerificationStatus.FOUND_UNVERIFIED_FULL_SIZE:
                foundUnverifiedFullSizeCount += 1
        return foundUnverifiedFullSizeCount

    def GetFoundUnverifiedNotFullSizeCount(self):
        foundUnverifiedNotFullSizeCount = 0
        for row in range(0, self.GetRowCount()):
            if self.verificationsData[row].GetStatus() == \
                    VerificationStatus.FOUND_UNVERIFIED_NOT_FULL_SIZE:
                foundUnverifiedNotFullSizeCount += 1
        return foundUnverifiedNotFullSizeCount

    def GetFailedCount(self):
        failedCount = 0
        for row in range(0, self.GetRowCount()):
            if self.verificationsData[row].GetStatus() == VerificationStatus.FAILED:
                failedCount += 1
        return failedCount


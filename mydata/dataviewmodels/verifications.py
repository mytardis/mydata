"""
Represents the Verifications tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

# pylint: disable=missing-docstring

import threading
import traceback

from mydata.models.verification import VerificationStatus
from mydata.dataviewmodels.uploads import ColumnType
from mydata.logs import logger

import wx
if wx.version().startswith("3.0.3.dev"):
    from wx.dataview import DataViewIndexListModel  # pylint: disable=no-name-in-module
else:
    from wx.dataview import PyDataViewIndexListModel as DataViewIndexListModel


class VerificationsModel(DataViewIndexListModel):
    """
    Represents the Verifications tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.foldersModel = None
        self.verificationsData = list()
        DataViewIndexListModel.__init__(self, len(self.verificationsData))
        # Unfiltered verifications data:
        self.uvd = self.verificationsData
        # Filtered verifications data:
        self.fvd = list()
        self.filtered = False
        self.searchString = ""
        self.columnNames = ("Id", "Folder", "Subdirectory", "Filename",
                            "Message")
        self.columnKeys = ("dataViewId", "folder", "subdirectory", "filename",
                           "message")
        self.defaultColumnWidths = (40, 170, 170, 200, 500)
        self.columnTypes = (ColumnType.TEXT, ColumnType.TEXT, ColumnType.TEXT,
                            ColumnType.TEXT, ColumnType.TEXT)
        # This is the largest ID value which has been used in this model.
        # It may no longer exist, i.e. if we delete the row with the
        # largest ID, we don't decrement the maximum ID.
        self.maxDataViewId = 0

    def SetFoldersModel(self, foldersModel):
        self.foldersModel = foldersModel

    def Filter(self, searchString):
        # pylint: disable=too-many-branches
        self.searchString = searchString
        query = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.uvd = list(self.verificationsData)

        for row in reversed(range(0, self.GetRowCount())):
            verif = self.verificationsData[row]
            if query not in verif.GetFilename().lower() and \
                    query not in verif.GetFolder().lower() and \
                    query not in verif.GetSubdirectory().lower() and \
                    query not in verif.GetMessage().lower():
                self.fvd.append(verif)
                del self.verificationsData[row]
                # Notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            fvd = self.fvd[filteredRow]
            if query in fvd.GetFilename().lower() or \
                    query in fvd.GetFolder().lower() or \
                    query in fvd.GetSubdirectory().lower() or \
                    query in fvd.GetMessage().lower():
                # Model doesn't care about currently sorted column.
                # Always use ID.
                row = 0
                col = 0
                ascending = True
                while row < self.GetRowCount() and \
                        self.CompareVerifications(self.verificationsData[row],
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

    def GetColumnType(self, col):
        """
        All of our columns are strings.  If the model or the renderers
        in the view are other types then that should be reflected here.
        """
        # pylint: disable=arguments-differ
        # pylint: disable=unused-argument
        # pylint: disable=no-self-use
        return "string"

    def GetValueByRow(self, row, col):
        """
        This method is called to provide the verificationsData object for a
        particular row, col
        """
        # pylint: disable=arguments-differ
        columnKey = self.GetColumnKeyName(col)
        return str(self.verificationsData[row].GetValueForKey(columnKey))

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
        return len(self.verificationsData)

    def GetUnfilteredRowCount(self):
        return len(self.uvd)

    def GetFilteredRowCount(self):
        return len(self.fvd)

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
        # pylint: disable=no-self-use
        return len(self.verificationsData)

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

    # Unlike the previous Compare method, in this case, the verifications
    # don't need to be visible in the current (possibly filtered) data view.
    def CompareVerifications(self, verification1, verification2,
                             col, ascending):
        # Swap sort order?
        if not ascending:
            verification2, verification1 = verification1, verification2
        if col == 0:
            return cmp(int(verification1.GetDataViewId()),
                       int(verification2.GetDataViewId()))
        else:
            return cmp(verification1.GetValueForKey(self.columnKeys[col]),
                       verification2.GetValueForKey(self.columnKeys[col]))

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
        # pylint: disable=bare-except
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
            if self.verificationsData[row].GetStatus() == \
                    VerificationStatus.FAILED:
                failedCount += 1
        return failedCount

    def GetCompletedCount(self):
        foundCompletedCount = 0
        for row in range(0, self.GetRowCount()):
            if self.verificationsData[row].GetComplete():
                foundCompletedCount += 1
        return foundCompletedCount

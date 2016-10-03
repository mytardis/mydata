"""
Represents the Verifications tab of MyData's main window,
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

from mydata.models.verification import VerificationStatus
from mydata.dataviewmodels.uploads import ColumnType
from mydata.logs import logger


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
        self.columnNames = ("Id", "Folder", "Subdirectory", "Filename",
                            "Message")
        self.columnKeys = ("dataViewId", "folder", "subdirectory", "filename",
                           "message")
        self.defaultColumnWidths = (40, 170, 170, 200, 500)
        self.columnTypes = (ColumnType.TEXT, ColumnType.TEXT, ColumnType.TEXT,
                            ColumnType.TEXT, ColumnType.TEXT)
        self.maxDataViewId = 0
        self.maxDataViewIdLock = threading.Lock()
        self.completedCount = 0
        self.completedCountLock = threading.Lock()

    def SetFoldersModel(self, foldersModel):
        self.foldersModel = foldersModel

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

    def Compare(self, item1, item2, col, ascending):
        """
        This is called to assist with sorting the data in the view.  The
        first two args are instances of the DataViewItem class, so we
        need to convert them to row numbers with the GetRow method.
        Then it's just a matter of fetching the right values from our
        data set and comparing them.  The return value is -1, 0, or 1,
        just like Python's cmp() function.
        """
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

        self.maxDataViewId = 0
        self.completedCount = 0

    def GetMaxDataViewId(self):
        return self.maxDataViewId

    def SetMaxDataViewId(self, dataViewId):
        self.maxDataViewIdLock.acquire()
        self.maxDataViewId = dataViewId
        self.maxDataViewIdLock.release()

    def AddRow(self, verificationModel):
        self.verificationsData.append(verificationModel)
        # Notify views
        if threading.current_thread().name == "MainThread":
            self.RowAppended()
        else:
            wx.CallAfter(self.RowAppended)

        self.SetMaxDataViewId(verificationModel.GetDataViewId())

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

    def SetComplete(self, verificationModel):
        verificationModel.SetComplete()
        self.completedCountLock.acquire()
        try:
            self.completedCount += 1
        finally:
            self.completedCountLock.release()

    def MessageUpdated(self, verificationModel):
        for row in reversed(range(0, self.GetCount())):
            if self.verificationsData[row] == verificationModel:
                col = self.columnNames.index("Message")
                wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def GetFoundVerifiedCount(self):
        foundVerifiedCount = 0
        for row in reversed(range(0, self.GetRowCount())):
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
        return self.completedCount

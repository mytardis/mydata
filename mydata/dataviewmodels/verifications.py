"""
Represents the Verifications tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import threading

import wx

from ..models.verification import VerificationStatus
from .uploads import ColumnType
from .dataview import DataViewIndexListModel
from .dataview import TryRowValueChanged


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
        """
        Get column name
        """
        return self.columnNames[col]

    def GetColumnKeyName(self, col):
        """
        Get column key name
        """
        return self.columnKeys[col]

    def GetDefaultColumnWidth(self, col):
        """
        Get default column width
        """
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

    def DeleteAllRows(self):
        """
        Delete all rows
        """
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
        """
        Get maximum dataview ID
        """
        return self.maxDataViewId

    def SetMaxDataViewId(self, dataViewId):
        """
        Set maximum dataview ID
        """
        self.maxDataViewIdLock.acquire()
        self.maxDataViewId = dataViewId
        self.maxDataViewIdLock.release()

    def AddRow(self, verificationModel):
        """
        Add a row
        """
        self.verificationsData.append(verificationModel)
        # Notify views
        if threading.current_thread().name == "MainThread":
            self.RowAppended()
        else:
            wx.CallAfter(self.RowAppended)

        self.SetMaxDataViewId(verificationModel.GetDataViewId())

    def SetComplete(self, verificationModel):
        """
        Set verificationModel's status to complete
        """
        verificationModel.SetComplete()
        self.completedCountLock.acquire()
        try:
            self.completedCount += 1
        finally:
            self.completedCountLock.release()

    def MessageUpdated(self, verificationModel):
        """
        Update verificationModel's message
        """
        for row in reversed(range(0, self.GetCount())):
            if self.verificationsData[row] == verificationModel:
                col = self.columnNames.index("Message")
                wx.CallAfter(TryRowValueChanged, self, row, col)
                break

    def GetFoundVerifiedCount(self):
        """
        Return the number of files which were found on the MyTardis server
        and were verified by MyTardis
        """
        foundVerifiedCount = 0
        for row in reversed(range(0, self.GetRowCount())):
            if self.verificationsData[row].GetStatus() == \
                    VerificationStatus.FOUND_VERIFIED:
                foundVerifiedCount += 1
        return foundVerifiedCount

    def GetNotFoundCount(self):
        """
        Return the number of files which were not found on the MyTardis server
        """
        notFoundCount = 0
        for row in range(0, self.GetRowCount()):
            if self.verificationsData[row].GetStatus() == \
                    VerificationStatus.NOT_FOUND:
                notFoundCount += 1
        return notFoundCount

    def GetFoundUnverifiedFullSizeCount(self):
        """
        Return the number of files which were found on the MyTardis server
        which are unverified on MyTardis but full size
        """
        foundUnverifiedFullSizeCount = 0
        for row in range(0, self.GetRowCount()):
            if self.verificationsData[row].GetStatus() == \
                    VerificationStatus.FOUND_UNVERIFIED_FULL_SIZE:
                foundUnverifiedFullSizeCount += 1
        return foundUnverifiedFullSizeCount

    def GetFoundUnverifiedNotFullSizeCount(self):
        """
        Return the number of files which were found on the MyTardis server
        which are unverified on MyTardis and incomplete
        """
        foundUnverifiedNotFullSizeCount = 0
        for row in range(0, self.GetRowCount()):
            if self.verificationsData[row].GetStatus() == \
                    VerificationStatus.FOUND_UNVERIFIED_NOT_FULL_SIZE:
                foundUnverifiedNotFullSizeCount += 1
        return foundUnverifiedNotFullSizeCount

    def GetFailedCount(self):
        """
        Return the number of files whose MyTardis lookups failed
        """
        failedCount = 0
        for row in range(0, self.GetRowCount()):
            if self.verificationsData[row].GetStatus() == \
                    VerificationStatus.FAILED:
                failedCount += 1
        return failedCount

    def GetCompletedCount(self):
        """
        Return the number of files which MyData has finished looking
        up on the MyTardis server.
        """
        return self.completedCount

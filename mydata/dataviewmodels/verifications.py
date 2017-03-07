"""
Represents the Verifications tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import threading

import wx

from ..models.verification import VerificationStatus
from .dataview import MyDataDataViewModel


class VerificationsModel(MyDataDataViewModel):
    """
    Represents the Verifications tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-many-public-methods
    # pylint: disable=arguments-differ
    def __init__(self):
        super(VerificationsModel, self).__init__()
        self.foldersModel = None
        self.columnNames = ["Id", "Folder", "Subdirectory", "Filename",
                            "Message"]
        self.columnKeys = ["dataViewId", "folderName", "subdirectory",
                           "filename", "message"]
        self.defaultColumnWidths = [40, 170, 170, 200, 500]
        self.completedCount = 0
        self.completedCountLock = threading.Lock()

    def DeleteAllRows(self):
        """
        Delete all rows
        """
        super(VerificationsModel, self).DeleteAllRows()
        self.completedCount = 0

    def SetComplete(self, verificationModel):
        """
        Set verificationModel's status to complete
        """
        verificationModel.complete = True
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
            if self.rowsData[row] == verificationModel:
                col = self.columnNames.index("Message")
                wx.CallAfter(self.TryRowValueChanged, row, col)
                break

    def GetFoundVerifiedCount(self):
        """
        Return the number of files which were found on the MyTardis server
        and were verified by MyTardis
        """
        foundVerifiedCount = 0
        for row in reversed(range(0, self.GetRowCount())):
            if self.rowsData[row].status == \
                    VerificationStatus.FOUND_VERIFIED:
                foundVerifiedCount += 1
        return foundVerifiedCount

    def GetNotFoundCount(self):
        """
        Return the number of files which were not found on the MyTardis server
        """
        notFoundCount = 0
        for row in range(0, self.GetRowCount()):
            if self.rowsData[row].status == \
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
            if self.rowsData[row].status == \
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
            if self.rowsData[row].status == \
                    VerificationStatus.FOUND_UNVERIFIED_NOT_FULL_SIZE:
                foundUnverifiedNotFullSizeCount += 1
        return foundUnverifiedNotFullSizeCount

    def GetFailedCount(self):
        """
        Return the number of files whose MyTardis lookups failed
        """
        failedCount = 0
        for row in range(0, self.GetRowCount()):
            if self.rowsData[row].status == \
                    VerificationStatus.FAILED:
                failedCount += 1
        return failedCount

    def GetCompletedCount(self):
        """
        Return the number of files which MyData has finished looking
        up on the MyTardis server.
        """
        return self.completedCount

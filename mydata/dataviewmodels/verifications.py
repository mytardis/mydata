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

        self.totals = dict(
            completed=0,
            notFound=0,
            foundVerified=0,
            foundUnverifiedFullSize=0,
            foundUnverifiedNotFullSize=0,
            failed=0)

        self.countLocks = dict(
            completed=threading.Lock(),
            notFound=threading.Lock(),
            foundVerified=threading.Lock(),
            foundUnverifiedFullSize=threading.Lock(),
            foundUnverifiedNotFullSize=threading.Lock(),
            failed=threading.Lock())

    def DeleteAllRows(self):
        """
        Delete all rows
        """
        super(VerificationsModel, self).DeleteAllRows()
        self.totals = dict(
            completed=0,
            notFound=0,
            foundVerified=0,
            foundUnverifiedFullSize=0,
            foundUnverifiedNotFullSize=0,
            failed=0)

    def SetComplete(self, verificationModel):
        """
        Set verificationModel's status to complete
        """
        verificationModel.complete = True
        with self.countLocks['completed']:
            self.totals['completed'] += 1

    def SetNotFound(self, verificationModel):
        """
        Set verificationModel's status to not found
        """
        verificationModel.status = VerificationStatus.NOT_FOUND
        with self.countLocks['notFound']:
            self.totals['notFound'] += 1

    def SetFoundVerified(self, verificationModel):
        """
        Set verificationModel's status to found verified
        """
        verificationModel.status = VerificationStatus.FOUND_VERIFIED
        with self.countLocks['foundVerified']:
            self.totals['foundVerified'] += 1

    def SetFoundUnverifiedFullSize(self, verificationModel):
        """
        Set verificationModel's status to found unverified full size
        """
        verificationModel.status = \
            VerificationStatus.FOUND_UNVERIFIED_FULL_SIZE
        with self.countLocks['foundUnverifiedFullSize']:
            self.totals['foundUnverifiedFullSize'] += 1

    def SetFoundUnverifiedNotFullSize(self, verificationModel):
        """
        Set verificationModel's status to found unverified not full size
        """
        verificationModel.status = \
            VerificationStatus.FOUND_UNVERIFIED_NOT_FULL_SIZE
        with self.countLocks['foundUnverifiedNotFullSize']:
            self.totals['foundUnverifiedNotFullSize'] += 1

    def SetFailed(self, verificationModel):
        """
        Set verificationModel's status to failed
        """
        verificationModel.status = VerificationStatus.FAILED
        with self.countLocks['failed']:
            self.totals['failed'] += 1

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
        return self.totals['foundVerified']

    def GetNotFoundCount(self):
        """
        Return the number of files which were not found on the MyTardis server
        """
        return self.totals['notFound']

    def GetFoundUnverifiedFullSizeCount(self):
        """
        Return the number of files which were found on the MyTardis server
        which are unverified on MyTardis but full size
        """
        return self.totals['foundUnverifiedFullSize']

    def GetFoundUnverifiedNotFullSizeCount(self):
        """
        Return the number of files which were found on the MyTardis server
        which are unverified on MyTardis and incomplete
        """
        return self.totals['foundUnverifiedNotFullSize']

    def GetFailedCount(self):
        """
        Return the number of files whose MyTardis lookups failed
        """
        return self.totals['failed']

    def GetCompletedCount(self):
        """
        Return the number of files which MyData has finished looking
        up on the MyTardis server.
        """
        return self.totals['completed']

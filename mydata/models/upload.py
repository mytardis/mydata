"""
Model class for a datafile upload, which appears as one row in
the Uploads view of MyData's main window.
"""

# pylint: disable=missing-docstring

import os
import sys
import signal
import traceback

from mydata.logs import logger
from mydata.utils import HumanReadableSizeString


class UploadStatus(object):
    """
    Enumerated data type.
    """
    # pylint: disable=invalid-name
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3
    PAUSED = 4
    CANCELED = 5


class UploadModel(object):
    """
    Model class for a datafile upload, which appears as one row in
    the Uploads view of MyData's main window.
    """
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    def __init__(self, dataViewId, folderModel, dataFileIndex):
        self.dataViewId = dataViewId
        self.dataFileIndex = dataFileIndex
        self.dataFileId = None
        self.dfoId = None
        self.existingUnverifiedDatafile = None
        self.folder = folderModel.GetFolder()
        self.subdirectory = folderModel.GetDataFileDirectory(dataFileIndex)
        self.filename = folderModel.GetDataFileName(dataFileIndex)
        self.filesize = ""  # Human-readable string displayed in data view

        # Number of bytes uploaded (used to render progress bar):
        self.bytesUploaded = 0
        # Number of bytes previously uploaded, or None if the file is not yet
        # on the staging area:
        self.bytesUploadedPreviously = None
        # self.progress = 0.0  # Percentage used to render progress bar
        self.progress = 0  # Percentage used to render progress bar
        self.status = UploadStatus.NOT_STARTED
        self.message = ""
        self.speed = ""
        self.traceback = None
        self.bufferedReader = None
        self.scpUploadProcessPid = None
        self.fileSize = 0  # File size long integer in bytes
        self.canceled = False
        self.retries = 0

        self.startTime = None
        # The latest time at which upload progress has been measured:
        self.latestTime = None

        # After the file is uploaded, MyData will request verification
        # after a short delay.  During that delay, the countdown timer
        # will be stored in the UploadModel so that it can be canceled
        # if necessary:
        self.verificationTimer = None

    def GetDataViewId(self):
        return self.dataViewId

    def GetFilename(self):
        return self.filename

    def GetBytesUploaded(self):
        return self.bytesUploaded

    def SetBytesUploaded(self, bytesUploaded):
        self.bytesUploaded = bytesUploaded
        if self.bytesUploaded and self.latestTime:
            elapsedTime = self.latestTime - self.startTime
            if elapsedTime.total_seconds():
                speedMBs = (float(self.bytesUploaded) / 1000000.0
                            / elapsedTime.total_seconds())
                if speedMBs >= 1.0:
                    self.speed = "%3.1f MB/s" % speedMBs
                else:
                    self.speed = "%3.1f KB/s" % (speedMBs * 1000.0)

    def GetBytesUploadedPreviously(self):
        return self.bytesUploadedPreviously

    def SetBytesUploadedPreviously(self, bytesUploadedPreviously):
        self.bytesUploadedPreviously = bytesUploadedPreviously

    def GetProgress(self):
        return self.progress

    def SetProgress(self, progress):
        self.progress = progress
        if 0 < progress < 100:
            self.status = UploadStatus.IN_PROGRESS

    def GetStatus(self):
        return self.status

    def SetStatus(self, status):
        self.status = status

    def GetMessage(self):
        return self.message

    def SetMessage(self, message):
        self.message = message

    def GetSpeed(self):
        return self.speed

    def SetStartTime(self, startTime):
        self.startTime = startTime

    def SetLatestTime(self, latestTime):
        self.latestTime = latestTime
        if self.bytesUploaded and self.latestTime:
            elapsedTime = self.latestTime - self.startTime
            if elapsedTime.total_seconds():
                speedMBs = (float(self.bytesUploaded) / 1000000.0
                            / elapsedTime.total_seconds())
                if speedMBs >= 1.0:
                    self.speed = "%3.1f MB/s" % speedMBs
                else:
                    self.speed = "%3.1f KB/s" % (speedMBs * 1000.0)

    def GetTraceback(self):
        return self.traceback

    def SetTraceback(self, trace):
        self.traceback = trace

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetDataFileIndex(self):
        return self.dataFileIndex

    def GetBufferedReader(self):
        """
        Only used with UploadMethod.HTTP_POST
        """
        return self.bufferedReader

    def SetBufferedReader(self, bufferedReader):
        """
        Only used with UploadMethod.HTTP_POST
        """
        self.bufferedReader = bufferedReader

    def GetScpUploadProcessPid(self):
        return getattr(self, "scpUploadProcessPid", None)

    def SetScpUploadProcessPid(self, scpUploadProcessPid):
        self.scpUploadProcessPid = scpUploadProcessPid

    def GetRelativePathToUpload(self):
        if self.subdirectory != "":
            return os.path.join(self.subdirectory, self.filename)
        else:
            return self.filename

    def Cancel(self):
        try:
            self.canceled = True
            if self.verificationTimer:
                try:
                    self.verificationTimer.cancel()
                except:
                    logger.error(traceback.format_exc())
            if self.bufferedReader is not None:
                self.bufferedReader.close()
                logger.debug("Closed buffered reader for \"" +
                             self.GetRelativePathToUpload() +
                             "\".")
            if self.scpUploadProcessPid:
                if sys.platform.startswith("win"):
                    os.kill(self.scpUploadProcessPid, signal.SIGABRT)
                else:
                    os.kill(self.scpUploadProcessPid, signal.SIGKILL)
        except:
            logger.warning(traceback.format_exc())

    def SetFileSize(self, fileSize):
        self.fileSize = fileSize
        self.filesize = HumanReadableSizeString(self.fileSize)

    def GetFileSize(self):
        return self.fileSize

    def Canceled(self):
        return self.canceled

    def GetRetries(self):
        return self.retries

    def IncrementRetries(self):
        self.retries += 1

    def GetDataFileId(self):
        return self.dataFileId

    def SetDataFileId(self, dataFileId):
        self.dataFileId = dataFileId

    def GetExistingUnverifiedDatafile(self):
        return self.existingUnverifiedDatafile

    def SetExistingUnverifiedDatafile(self, existingUnverifiedDatafile):
        self.existingUnverifiedDatafile = existingUnverifiedDatafile
        if self.existingUnverifiedDatafile:
            self.SetDataFileId(self.existingUnverifiedDatafile.GetId())
            replicas = self.existingUnverifiedDatafile.GetReplicas()
            if len(replicas) == 1:
                self.SetDfoId(replicas[0].GetId())

    def GetDfoId(self):
        """
        Get the DataFileObject ID, also known as the replica ID.
        """
        return self.dfoId

    def SetDfoId(self, dfoId):
        """
        Set the DataFileObject ID, also known as the replica ID.
        """
        self.dfoId = dfoId

    def GetVerificationTimer(self):
        """
        After the file is uploaded, MyData will request verification
        after a short delay.  During that delay, the countdown timer
        will be stored in the UploadModel so that it can be canceled
        if necessary
        """
        return self.verificationTimer

    def SetVerificationTimer(self, verificationTimer):
        """
        After the file is uploaded, MyData will request verification
        after a short delay.  During that delay, the countdown timer
        will be stored in the UploadModel so that it can be canceled
        if necessary
        """
        self.verificationTimer = verificationTimer

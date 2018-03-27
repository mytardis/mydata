"""
Model class for a datafile upload, which appears as one row in
the Uploads view of MyData's main window.
"""
import os
import sys
import signal
import traceback

from ..logs import logger
from ..utils import HumanReadableSizeString


class UploadStatus(object):
    """
    Enumerated data type.

    This is used to update the status seen in the Uploads view.
    Stored in an UploadModel instance's status attribute, this
    field
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
        self.folderName = folderModel.folderName
        self.subdirectory = folderModel.GetDataFileDirectory(dataFileIndex)
        self.filename = folderModel.GetDataFileName(dataFileIndex)
        # Human-readable string displayed in data view:
        self.filesizeString = ""

        # Number of bytes uploaded (used to render progress bar):
        self.bytesUploaded = 0
        self.progress = 0  # Percentage used to render progress bar
        self.status = UploadStatus.NOT_STARTED
        self.message = ""
        self.speed = ""
        self.traceback = None
        self._fileSize = 0  # File size long integer in bytes
        self.canceled = False
        self.retries = 0

        # Only used with UploadMethod.HTTP_POST:
        self.bufferedReader = None

        # Only used with UploadMethod.VIA_STAGING:
        self.scpUploadProcessPid = None
        self._existingUnverifiedDatafile = None
        # The DataFileObject ID, also known as the replica ID:
        self.dfoId = None
        # Number of bytes previously uploaded, or None if the file is not yet
        # on the staging area:
        self.bytesUploadedPreviously = None

        self.startTime = None
        # The latest time at which upload progress has been measured:
        self.latestTime = None

        # After the file is uploaded, MyData will request verification
        # after a short delay.  During that delay, the countdown timer
        # will be stored in the UploadModel so that it can be canceled
        # if necessary:
        self.verificationTimer = None

    def SetBytesUploaded(self, bytesUploaded):
        """
        Set the number of bytes uploaded and update
        the elapsed time and upload speed.
        """
        self.bytesUploaded = bytesUploaded
        if self.bytesUploaded and self.latestTime:
            elapsedTime = self.latestTime - self.startTime
            if elapsedTime.total_seconds():
                speedMBs = (float(self.bytesUploaded) / 1000000.0 /
                            elapsedTime.total_seconds())
                if speedMBs >= 1.0:
                    self.speed = "%3.1f MB/s" % speedMBs
                else:
                    self.speed = "%3.1f KB/s" % (speedMBs * 1000.0)

    def SetProgress(self, progress):
        """
        Set upload progress and update UploadStatus.
        """
        self.progress = progress
        if 0 < progress < 100:
            self.status = UploadStatus.IN_PROGRESS

    def SetLatestTime(self, latestTime):
        """
        Set the latest time at which this upload is/was still progressing.

        This is updated while the upload is still in progress, so we can
        provide real time upload speed estimates.
        """
        self.latestTime = latestTime
        if self.bytesUploaded and self.latestTime:
            elapsedTime = self.latestTime - self.startTime
            if elapsedTime.total_seconds():
                speedMBs = (float(self.bytesUploaded) / 1000000.0 /
                            elapsedTime.total_seconds())
                if speedMBs >= 1.0:
                    self.speed = "%3.1f MB/s" % speedMBs
                else:
                    self.speed = "%3.1f KB/s" % (speedMBs * 1000.0)

    def GetValueForKey(self, key):
        """
        Return value of field from the UploadModel
        to display in the Uploads view
        """
        return getattr(self, key)

    def GetRelativePathToUpload(self):
        """
        Get the local path to this UploadModel's file,
        relative to the dataset folder
        """
        if self.subdirectory != "":
            relpath = os.path.join(self.subdirectory, self.filename)
        else:
            relpath = self.filename
        return relpath

    def Cancel(self):
        """
        Abort this upload
        """
        try:
            self.canceled = True
            self.status = UploadStatus.CANCELED
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

    @property
    def fileSize(self):
        """
        Return the file-to-be-uploaded's file size
        """
        return self._fileSize

    @fileSize.setter
    def fileSize(self, fileSize):
        """
        Record the file-to-be-uploaded's file size and update the
        human-readable string version of the file size
        """
        self._fileSize = fileSize
        self.filesizeString = HumanReadableSizeString(self._fileSize)

    @property
    def existingUnverifiedDatafile(self):
        """
        Return the existing unverified DataFile record (if any)
        associated with this upload
        """
        return self._existingUnverifiedDatafile

    @existingUnverifiedDatafile.setter
    def existingUnverifiedDatafile(self, existingUnverifiedDatafile):
        """
        Record an existing unverified DataFile
        """
        self._existingUnverifiedDatafile = existingUnverifiedDatafile
        if self._existingUnverifiedDatafile:
            self.dataFileId = self._existingUnverifiedDatafile.datafileId
            replicas = self._existingUnverifiedDatafile.replicas
            if len(replicas) == 1:
                self.dfoId = replicas[0].dfoId

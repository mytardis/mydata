"""
Model class for a datafile upload, which appears as one row in
the Uploads view of MyData's main window.
"""

# pylint: disable=missing-docstring

import os
import sys
import signal
import traceback
import psutil

from mydata.logs import logger
from mydata.utils import PidIsRunning
from mydata.utils import HumanReadableSizeString


class UploadStatus(object):
    """
    Enumerated data type.
    """
    # pylint: disable=invalid-name
    # pylint: disable=too-few-public-methods
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3
    PAUSED = 4


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
        self.traceback = None
        self.bufferedReader = None
        self.scpUploadProcess = None
        self.fileSize = 0  # File size long integer in bytes
        self.canceled = False
        self.retries = 0

    def GetDataViewId(self):
        return self.dataViewId

    def GetFilename(self):
        return self.filename

    def GetBytesUploaded(self):
        return self.bytesUploaded

    def SetBytesUploaded(self, bytesUploaded):
        self.bytesUploaded = bytesUploaded

    def GetBytesUploadedPreviously(self):
        return self.bytesUploadedPreviously

    def SetBytesUploadedPreviously(self, bytesUploadedPreviously):
        self.bytesUploadedPreviously = bytesUploadedPreviously

    def GetProgress(self):
        return self.progress

    def SetProgress(self, progress):
        self.progress = progress
        if progress > 0 and progress < 100:
            self.status = UploadStatus.IN_PROGRESS

    def GetStatus(self):
        return self.status

    def SetStatus(self, status):
        self.status = status

    def GetMessage(self):
        return self.message

    def SetMessage(self, message):
        self.message = message

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

    def GetScpUploadProcess(self):
        if hasattr(self, "scpUploadProcess"):
            return self.scpUploadProcess
        else:
            return None

    def SetScpUploadProcess(self, scpUploadProcess):
        self.scpUploadProcess = scpUploadProcess

    def GetRelativePathToUpload(self):
        if self.subdirectory != "":
            return os.path.join(self.subdirectory, self.filename)
        else:
            return self.filename

    def Cancel(self):
        try:
            self.canceled = True
            # logger.debug("Canceling upload \"" +
            #              self.GetRelativePathToUpload() + "\".")
            if self.bufferedReader is not None:
                self.bufferedReader.close()
                logger.debug("Closed buffered reader for \"" +
                             self.GetRelativePathToUpload() +
                             "\".")
            scpUploadProcess = self.GetScpUploadProcess()
            if scpUploadProcess and PidIsRunning(scpUploadProcess.pid):
                self.scpUploadProcess.terminate()
                # Check if the process has really
                # terminated and force kill if not.
                try:
                    pid = self.scpUploadProcess.pid
                    # See if this throws psutil.NoSuchProcess:
                    _ = psutil.Process(int(pid))
                    if sys.platform.startswith("win"):
                        # pylint: disable=no-member
                        os.kill(pid, signal.CTRL_C_EVENT)
                    else:
                        os.kill(pid, signal.SIGKILL)  # pylint: disable=no-member
                    logger.debug("Force killed SCP upload process for %s"
                                 % self.GetRelativePathToUpload())
                except psutil.NoSuchProcess:
                    logger.debug("SCP upload process for %s was terminated "
                                 "gracefully."
                                 % self.GetRelativePathToUpload())
        except:  # pylint: disable=bare-except
            logger.error(traceback.format_exc())

    def SetFileSize(self, fileSize):
        self.fileSize = fileSize
        self.filesize = HumanReadableSizeString(self.fileSize)

    def Canceled(self):
        return self.canceled

    def GetRetries(self):
        return self.retries

    def IncrementRetries(self):
        self.retries += 1

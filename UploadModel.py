from logger.Logger import logger
import os
import sys
import signal
import traceback
import psutil


class UploadStatus:
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3
    PAUSED = 4


class UploadModel():
    def __init__(self, dataViewId, folderModel, dataFileIndex):
        self.dataViewId = dataViewId
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.folder = folderModel.GetFolder()
        self.subdirectory = folderModel.GetDataFileDirectory(dataFileIndex)
        self.filename = self.folderModel.GetDataFileName(dataFileIndex)
        self.filesize = ""
        self.bytesUploaded = 0
        self.progress = 0.0  # Percentage used to render progress bar
        self.status = UploadStatus.NOT_STARTED
        self.message = ""
        self.bufferedReader = None
        self.scpUploadProcess = None
        self.fileSize = 0
        self.canceled = False

    def GetDataViewId(self):
        return self.dataViewId

    def GetFilename(self):
        return self.filename

    def GetBytesUploaded(self):
        return self.bytesUploaded

    def SetBytesUploaded(self, bytesUploaded):
        self.bytesUploaded = bytesUploaded

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

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetFolderModel(self):
        return self.folderModel

    def GetDataFileIndex(self):
        return self.dataFileIndex

    def SetBufferedReader(self, bufferedReader):
        self.bufferedReader = bufferedReader

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
            logger.debug("Canceling upload \"" +
                         self.GetRelativePathToUpload() +
                         "\".")
            if self.bufferedReader is not None:
                self.bufferedReader.close()
                logger.debug("Closed buffered reader for \"" +
                             self.GetRelativePathToUpload() +
                             "\".")
            if self.scpUploadProcess is not None:
                pid = self.scpUploadProcess.pid

                self.scpUploadProcess.terminate()

                # Check if the process has really
                # terminated and force kill if not.
                try:
                    # See if this throws psutil.NoSuchProcess:
                    p = psutil.Process(int(pid))
                    if sys.platform.startswith("win"):
                        os.kill(pid, signal.CTRL_C_EVENT)
                    else:
                        os.kill(pid, signal.SIGKILL)
                    logger.debug("Force killed ssh upload process for %s"
                                 % self.GetRelativePathToUpload())
                except psutil.NoSuchProcess:
                    logger.debug("ssh upload process for %s was terminated "
                                 "gracefully."
                                 % self.GetRelativePathToUpload())
        except:
            logger.error(traceback.format_exc())

    def SetFileSize(self, fileSize):
        self.fileSize = fileSize
        self.filesize = HumanReadableSizeString(self.fileSize)

    def Canceled(self):
        return self.canceled


def HumanReadableSizeString(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.0f %s" % (num, x)
        num /= 1024.0
    return "%3.0f %s" % (num, 'TB')

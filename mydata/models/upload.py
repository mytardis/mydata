import os
import sys
import signal
import traceback
import psutil

from mydata.logs import logger


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
        self.filesize = ""  # Human-readable string displayed in data view
        self.bytesUploaded = 0
        self.bytesUploadedToStaging = None
        # self.progress = 0.0  # Percentage used to render progress bar
        self.progress = 0  # Percentage used to render progress bar
        self.status = UploadStatus.NOT_STARTED
        self.message = ""
        self.bufferedReader = None
        self.scpUploadProcess = None
        self.fileSize = 0  # File size long integer in bytes
        self.canceled = False
        self.retries = 0

        self.verificationModel = None

    def GetDataViewId(self):
        return self.dataViewId

    def GetFilename(self):
        return self.filename

    def GetBytesUploaded(self):
        return self.bytesUploaded

    def SetBytesUploaded(self, bytesUploaded):
        self.bytesUploaded = bytesUploaded

    def GetBytesUploadedToStaging(self):
        return self.bytesUploadedToStaging

    def SetBytesUploadedToStaging(self, bytesUploadedToStaging):
        self.bytesUploadedToStaging = bytesUploadedToStaging

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

    def GetSshMasterProcess(self):
        if hasattr(self, "sshMasterProcess"):
            return self.sshMasterProcess
        else:
            # return None
            return self.verificationModel.GetSshMasterProcess()

    def SetSshMasterProcess(self, sshMasterProcess):
        self.sshMasterProcess = sshMasterProcess

    def GetSshControlPath(self):
        if hasattr(self, "sshControlPath"):
            return self.sshControlPath
        else:
            # return None
            return self.verificationModel.GetSshControlPath()

    def SetSshControlPath(self, sshControlPath):
        self.sshControlPath = sshControlPath

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
                    p = psutil.Process(int(pid))
                    if sys.platform.startswith("win"):
                        os.kill(pid, signal.CTRL_C_EVENT)
                    else:
                        os.kill(pid, signal.SIGKILL)
                    logger.debug("Force killed SCP upload process for %s"
                                 % self.GetRelativePathToUpload())
                except psutil.NoSuchProcess:
                    logger.debug("SCP upload process for %s was terminated "
                                 "gracefully."
                                 % self.GetRelativePathToUpload())

            sshMasterProcess = self.GetSshMasterProcess()
            if sshMasterProcess and PidIsRunning(sshMasterProcess.pid):
                sshMasterProcess.terminate()
        except:
            logger.error(traceback.format_exc())

    def SetFileSize(self, fileSize):
        self.fileSize = fileSize
        self.filesize = HumanReadableSizeString(self.fileSize)

    def Canceled(self):
        return self.canceled

    def GetVerificationModel(self):
        return self.verificationModel

    def SetVerificationModel(self, verificationModel):
        self.verificationModel = verificationModel

    def GetRetries(self):
        return self.retries

    def IncrementRetries(self):
        self.retries += 1

    def GetMaxRetries(self):
        return 5  # FIXME: Magic number


def HumanReadableSizeString(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.0f %s" % (num, x)
        num /= 1024.0
    return "%3.0f %s" % (num, 'TB')


def PidIsRunning(pid):
    try:
        p = psutil.Process(int(pid))
        if p.status == psutil.STATUS_DEAD:
            return False
        if p.status == psutil.STATUS_ZOMBIE:
            return False
        return True  # Assume other status are valid
    except psutil.NoSuchProcess:
        return False

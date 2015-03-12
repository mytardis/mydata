class VerificationStatus:
    NOT_STARTED = 0
    IN_PROGRESS = 1
    # Not found on MyTardis, need to upload this file:
    NOT_FOUND = 2
    # Found on MyTardis (and verified), no need to upload this file:
    FOUND_VERIFIED = 3
    # Finished uploading to staging, waiting
    # for MyTardis to verify (don't re-upload):
    FOUND_UNVERIFIED_FULL_SIZE = 4
    # Partially uploaded to staging, need to resume upload or re-upload:
    FOUND_UNVERIFIED_NOT_FULL_SIZE = 5
    # Verification failed, should upload file, unless the failure
    # was so serious (e.g. no network) that we need to abort everything.
    FAILED = 6


class VerificationModel():

    def __init__(self, dataViewId, folderModel, dataFileIndex):
        self.dataViewId = dataViewId
        self.folderModel = folderModel
        self.folder = folderModel.GetFolder()
        self.subdirectory = folderModel.GetDataFileDirectory(dataFileIndex)
        self.dataFileIndex = dataFileIndex
        self.filename = self.folderModel.GetDataFileName(dataFileIndex)
        self.message = ""
        self.status = VerificationStatus.NOT_STARTED
        self.complete = False

    def GetDataViewId(self):
        return self.dataViewId

    def GetFilename(self):
        return self.filename

    def GetSubdirectory(self):
        return self.subdirectory

    def GetStatus(self):
        return self.status

    def SetComplete(self, complete=True):
        self.complete = complete

    def GetComplete(self):
        return self.complete

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

    def GetFolder(self):
        return self.folder

    def GetDataFileIndex(self):
        return self.dataFileIndex

    def GetSshMasterProcess(self):
        if hasattr(self, "sshMasterProcess"):
            return self.sshMasterProcess
        else:
            return None

    def SetSshMasterProcess(self, sshMasterProcess):
        self.sshMasterProcess = sshMasterProcess

    def GetSshControlPath(self):
        if hasattr(self, "sshControlPath"):
            return self.sshControlPath
        else:
            return None

    def SetSshControlPath(self, sshControlPath):
        self.sshControlPath = sshControlPath

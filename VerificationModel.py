class VerificationModel():
    def __init__(self, folderModel, dataFileIndex):
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.filename = self.folderModel.GetDataFileName(dataFileIndex)
        self.bytesUploadedToStaging = None

    def GetFilename(self):
        return self.filename

    def GetBytesUploadedToStaging(self):
        return self.bytesUploadedToStaging

    def SetBytesUploadedToStaging(self, bytesUploadedToStaging):
        self.bytesUploadedToStaging = bytesUploadedToStaging

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetFolderModel(self):
        return self.folderModel

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

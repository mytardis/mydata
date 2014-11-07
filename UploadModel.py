
class UploadStatus:
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3
    PAUSED = 4


class UploadModel():
    def __init__(self, id, folderModel, dataFileIndex):
        self.id = id
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.folder = folderModel.GetFolder()
        self.subdirectory = folderModel.GetDataFileDirectory(dataFileIndex)
        self.filename = self.folderModel.GetDataFileName(dataFileIndex)
        self.filesize = ""
        self.progress = 0.0
        self.status = UploadStatus.NOT_STARTED
        self.message = ""
        self.bufferedReader = None
        self.fileSize = 0

    def GetId(self):
        return self.id

    def GetFilename(self):
        return self.filename

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

    def Cancel(self):
        if self.bufferedReader is not None:
            self.bufferedReader.close()

    def SetFileSize(self, fileSize):

        self.fileSize = fileSize
        self.filesize = sizeof_fmt(self.fileSize)


def sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.0f %s" % (num, x)
        num /= 1024.0
    return "%3.0f %s" % (num, 'TB')

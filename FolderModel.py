import os
import urllib
import requests
import json

from DatasetModel import DatasetModel


class FolderModel():

    def __init__(self, id, folder, location, folder_type, owner_id,
                 foldersModel, usersModel, settingsModel):
        self.id = id
        self.folder = folder
        self.location = location
        absoluteFolderPath = os.path.join(location, folder)
        self.numFiles = sum([len(files) for dirName, _, files in
                             os.walk(absoluteFolderPath)])
        self.dataFilePaths = []
        self.dataFileDirectories = []
        for dirName, _, files in os.walk(absoluteFolderPath):
            for fileName in files:
                self.dataFilePaths.append(os.path.join(dirName, fileName))
                self.dataFileDirectories\
                    .append(os.path.relpath(dirName, absoluteFolderPath))
        for i in range(0, len(self.dataFileDirectories)):
            if self.dataFileDirectories[i] == ".":
                self.dataFileDirectories[i] = ""
            self.dataFileDirectories[i] = \
                self.dataFileDirectories[i].replace("\\", "/")
        self.created = ""
        self.status = "0 of %d files uploaded" % (self.numFiles,)
        self.folder_type = folder_type
        self.owner_id = owner_id
        self.foldersModel = foldersModel
        self.usersModel = usersModel
        self.settingsModel = settingsModel

        self.datasetModel = None

        self.dataFileUploaded = []
        for i in range(0, self.numFiles):
            self.dataFileUploaded.append(False)

        self.dataFileVerified = []
        for i in range(0, self.numFiles):
            self.dataFileVerified.append(False)

        self.numFilesUploaded = 0
        self.numFilesVerified = 0

    def SetDataFileUploaded(self, dataFileIndex, uploaded):

        self.dataFileUploaded[dataFileIndex] = uploaded
        self.numFilesUploaded = sum(self.dataFileUploaded)
        self.status = "%d of %d files uploaded" % (self.numFilesUploaded,
                                                   self.numFiles)

    def GetDatasetModel(self):
        return self.datasetModel

    def GetDataFilePath(self, dataFileIndex):
        return self.dataFilePaths[dataFileIndex]

    def GetDataFileDirectory(self, dataFileIndex):
        return self.dataFileDirectories[dataFileIndex]

    def GetDataFileName(self, dataFileIndex):
        return os.path.basename(self.dataFilePaths[dataFileIndex])

    def GetDataFileSize(self, dataFileIndex):
        return os.stat(self.GetDataFilePath(dataFileIndex)).st_size

    def SetExperiment(self, experimentModel):

        self.experimentModel = experimentModel

    def GetExperiment(self):
        return self.experimentModel

    def SetDatasetModel(self, datasetModel):

        self.datasetModel = datasetModel

    def GetId(self):
        return self.id

    def GetFolder(self):
        return self.folder

    def GetLocation(self):
        return self.location

    def GetNumFiles(self):
        return self.numFiles

    def GetCreated(self):
        return self.created

    def GetStatus(self):
        return self.status

    def GetFolderType(self):
        return self.folder_type

    def GetOwnerId(self):
        return self.owner_id

    def GetOwner(self):
        return self.usersModel.GetUserById(self.owner_id)

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetSettingsModel(self):
        return self.settingsModel

    def SetCreatedDate(self):

        import datetime
        absoluteFolderPath = os.path.join(self.location, self.folder)
        self.created = datetime.datetime\
            .fromtimestamp(os.stat(absoluteFolderPath).st_ctime)\
            .strftime('%Y-%m-%d')

    def Refresh(self):

        absoluteFolderPath = os.path.join(self.location, self.folder)
        self.numFiles = sum([len(files) for dirName, _, files in
                             os.walk(absoluteFolderPath)])
        self.dataFilePaths = []
        self.dataFileDirectories = []
        for dirName, _, files in os.walk(absoluteFolderPath):
            for fileName in files:
                self.dataFilePaths.append(os.path.join(dirName, fileName))
                self.dataFileDirectories.append(os.path.relpath(dirName,
                                                absoluteFolderPath))
        for i in range(0, len(self.dataFileDirectories)):
            if self.dataFileDirectories[i] == ".":
                self.dataFileDirectories[i] = ""
            self.dataFileDirectories[i] = \
                self.dataFileDirectories[i].replace("\\", "/")

        self.status = "0 of %d files uploaded" % (self.numFiles,)
        self.SetCreatedDate()
        modified = True
        return modified

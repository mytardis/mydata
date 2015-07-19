import os
import urllib
import requests
import json
from datetime import datetime
import traceback

from .dataset import DatasetModel
from mydata.logs import logger


class FolderModel():
    def __init__(self, dataViewId, folder, location,
                 userFolderName, groupFolderName, owner,
                 foldersModel, usersModel, settingsModel):
        self.dataViewId = dataViewId
        self.folder = folder
        self.location = location
        absoluteFolderPath = os.path.join(location, folder)
        self.numFiles = sum([len(files) for dirName, _, files in
                             os.walk(absoluteFolderPath)])
        self.dataFilePaths = []
        self.dataFileDirectories = []
        for dirName, _, files in os.walk(absoluteFolderPath):
            for fileName in sorted(files):
                self.dataFilePaths.append(os.path.join(dirName, fileName))
                self.dataFileDirectories\
                    .append(os.path.relpath(dirName, absoluteFolderPath))
        for i in range(0, len(self.dataFileDirectories)):
            if self.dataFileDirectories[i] == ".":
                self.dataFileDirectories[i] = ""
            self.dataFileDirectories[i] = \
                self.dataFileDirectories[i].replace("\\", "/")
        self.created = ""
        self.experimentTitle = ""
        self.group = None
        self.experimentTitleSetManually = False
        self.status = "0 of %d files uploaded" % (self.numFiles,)
        self.userFolderName = userFolderName
        self.groupFolderName = groupFolderName
        self.owner = owner
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

    def GetDataFileCreatedTime(self, dataFileIndex):
        absoluteFilePath = self.GetDataFilePath(dataFileIndex)
        try:
            createdTimeIsoString = datetime.fromtimestamp(
                os.stat(absoluteFilePath).st_ctime).isoformat()
            return createdTimeIsoString
        except:
            logger.error(traceback.format_exc())
            return None

    def SetExperiment(self, experimentModel):
        self.experimentModel = experimentModel

    def GetExperiment(self):
        return self.experimentModel

    def SetDatasetModel(self, datasetModel):
        self.datasetModel = datasetModel

    def GetDataViewId(self):
        return self.dataViewId

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

    def GetUserFolderName(self):
        return self.userFolderName

    def GetGroupFolderName(self):
        return self.groupFolderName

    def GetOwnerId(self):
        return self.owner.GetId()

    def GetOwner(self):
        return self.owner

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetSettingsModel(self):
        return self.settingsModel

    def SetCreatedDate(self):
        absoluteFolderPath = os.path.join(self.location, self.folder)
        self.created = datetime.fromtimestamp(
            os.stat(absoluteFolderPath).st_ctime)\
            .strftime('%Y-%m-%d')
        self.SetExperimentTitle()

    def GetExperimentTitle(self):
        return self.experimentTitle

    def SetExperimentTitle(self, experimentTitle=None):
        if experimentTitle is not None:
            self.experimentTitle = experimentTitle
            self.experimentTitleSetManually = True
        else:
            self.experimentTitle = \
                self.settingsModel.GetInstrumentName() + " " + self.created

    def ExperimentTitleSetManually(self):
        return self.experimentTitleSetManually

    def GetGroup(self):
        return self.group

    def SetGroup(self, group):
        self.group = group

    def Refresh(self):
        absoluteFolderPath = os.path.join(self.location, self.folder)
        self.numFiles = sum([len(files) for dirName, _, files in
                             os.walk(absoluteFolderPath)])
        self.dataFilePaths = []
        self.dataFileDirectories = []
        for dirName, _, files in os.walk(absoluteFolderPath):
            for fileName in sorted(files):
                self.dataFilePaths.append(os.path.join(dirName, fileName))
                self.dataFileDirectories\
                    .append(os.path.relpath(dirName, absoluteFolderPath))
        for i in range(0, len(self.dataFileDirectories)):
            if self.dataFileDirectories[i] == ".":
                self.dataFileDirectories[i] = ""
            self.dataFileDirectories[i] = \
                self.dataFileDirectories[i].replace("\\", "/")

        self.status = "0 of %d files uploaded" % (self.numFiles,)
        self.SetCreatedDate()
        modified = True
        return modified

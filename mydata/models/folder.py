"""
Model class representing a data folder which may or may not
have a corresponding dataset record in MyTardis.
"""

# pylint: disable=missing-docstring

import os
from datetime import datetime
import traceback
from fnmatch import fnmatch

from mydata.logs import logger


class FolderModel(object):
    """
    Model class representing a data folder which may or may not
    have a corresponding dataset record in MyTardis.
    """
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    def __init__(self, dataViewId, folder, location,
                 userFolderName, groupFolderName, owner,
                 foldersModel, usersModel, settingsModel):
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-locals
        self.settingsModel = settingsModel
        self.dataViewId = dataViewId
        self.folder = folder
        self.location = location
        absoluteFolderPath = os.path.join(location, folder)
        self.dataFilePaths = []
        self.dataFileDirectories = []
        self.numFiles = 0
        for dirname, _, files in os.walk(absoluteFolderPath):
            for filename in sorted(files):
                if settingsModel.UseIncludesFile() and \
                        not settingsModel.UseExcludesFile():
                    if not self.MatchesIncludes(filename):
                        logger.debug("Ignoring %s, not matching includes."
                                     % filename)
                        continue
                elif not settingsModel.UseIncludesFile() and \
                        settingsModel.UseExcludesFile():
                    if self.MatchesExcludes(filename):
                        logger.debug("Ignoring %s, matching excludes."
                                     % filename)
                        continue
                elif settingsModel.UseIncludesFile() and \
                        settingsModel.UseExcludesFile():
                    if self.MatchesExcludes(filename) and \
                            not self.MatchesIncludes(filename):
                        logger.debug("Ignoring %s, matching excludes "
                                     "and not matching includes."
                                     % filename)
                        continue
                self.numFiles += 1
                self.dataFilePaths.append(os.path.join(dirname, filename))
                self.dataFileDirectories\
                    .append(os.path.relpath(dirname, absoluteFolderPath))
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

        self.datasetModel = None
        self.experimentModel = None

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

    def GetDataFileRelPath(self, dataFileIndex):
        return os.path.relpath(self.GetDataFilePath(dataFileIndex),
                               self.settingsModel.GetDataDirectory())

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
        except:  # pylint: disable=bare-except
            logger.error(traceback.format_exc())
            return None

    def GetDataFileModifiedTime(self, dataFileIndex):
        absoluteFilePath = self.GetDataFilePath(dataFileIndex)
        try:
            modifiedTimeIsoString = datetime.fromtimestamp(
                os.stat(absoluteFilePath).st_mtime).isoformat()
            return modifiedTimeIsoString
        except:  # pylint: disable=bare-except
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

    def GetRelPath(self):
        return os.path.join(
            os.path.relpath(self.location,
                            self.settingsModel.GetDataDirectory()),
            self.folder)

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

    def GetExperimentTitle(self):
        return self.experimentTitle

    def SetExperimentTitle(self, title):
        self.experimentTitle = title
        self.experimentTitleSetManually = True

    def ExperimentTitleSetManually(self):
        return self.experimentTitleSetManually

    def GetGroup(self):
        return self.group

    def SetGroup(self, group):
        self.group = group

    def Refresh(self):
        absoluteFolderPath = os.path.join(self.location, self.folder)
        self.dataFilePaths = []
        self.dataFileDirectories = []
        self.numFiles = 0
        for dirname, _, files in os.walk(absoluteFolderPath):
            for filename in sorted(files):
                if self.settingsModel.UseIncludesFile() and \
                        not self.settingsModel.UseExcludesFile():
                    if not self.MatchesIncludes(filename):
                        logger.debug("Ignoring %s, not matching includes."
                                     % filename)
                        continue
                elif not self.settingsModel.UseIncludesFile() and \
                        self.settingsModel.UseExcludesFile():
                    if self.MatchesExcludes(filename):
                        logger.debug("Ignoring %s, matching excludes."
                                     % filename)
                        continue
                elif self.settingsModel.UseIncludesFile() and \
                        self.settingsModel.UseExcludesFile():
                    if self.MatchesExcludes(filename) and \
                            not self.MatchesIncludes(filename):
                        logger.debug("Ignoring %s, matching excludes "
                                     "and not matching includes."
                                     % filename)
                        continue
                self.numFiles += 1
                self.dataFilePaths.append(os.path.join(dirname, filename))
                self.dataFileDirectories\
                    .append(os.path.relpath(dirname, absoluteFolderPath))
        for i in range(0, len(self.dataFileDirectories)):
            if self.dataFileDirectories[i] == ".":
                self.dataFileDirectories[i] = ""
            self.dataFileDirectories[i] = \
                self.dataFileDirectories[i].replace("\\", "/")

        self.status = "0 of %d files uploaded" % (self.numFiles,)
        self.SetCreatedDate()
        modified = True
        return modified

    def MatchesIncludes(self, filename):
        """
        Return True if file matches at least one pattern in the includes
        file.
        """
        match = False
        with open(self.settingsModel.GetIncludesFile(), 'r') as includesFile:
            for glob in includesFile.readlines():
                glob = glob.decode('utf-8').strip()
                if glob == "":
                    continue
                if glob.startswith(";"):
                    continue
                if glob.startswith("#"):
                    continue
                match = match or fnmatch(filename, glob)
        return match

    def MatchesExcludes(self, filename):
        """
        Return True if file matches at least one pattern in the excludes
        file.
        """
        match = False
        with open(self.settingsModel.GetIncludesFile(), 'r') as includesFile:
            for glob in includesFile.readlines():
                glob = glob.decode('utf-8').strip()
                if glob == "":
                    continue
                if glob.startswith(";"):
                    continue
                if glob.startswith("#"):
                    continue
                match = match or fnmatch(filename, glob)
        return match

    def __hash__(self):
        return hash(self.dataViewId)

    def __eq__(self, other):
        return self.dataViewId == other.dataViewId

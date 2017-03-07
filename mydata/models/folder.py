"""
Model class representing a data folder which may or may not
have a corresponding dataset record in MyTardis.
"""
import os
import time
from datetime import datetime
import hashlib
import traceback
from fnmatch import fnmatch

from ..settings import SETTINGS
from ..logs import logger


class FolderModel(object):
    """
    Model class representing a data folder which may or may not
    have a corresponding dataset record in MyTardis.
    """
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def __init__(self, dataViewId, folderName, location, userFolderName,
                 groupFolderName, owner, isExperimentFilesFolder=False):
        # pylint: disable=too-many-locals
        self.dataViewId = dataViewId
        # The folder name, e.g. "Dataset1":
        self.folderName = folderName
        # The folder's location, e.g. "C:\Data\testuser1":
        self.location = location
        self.isExperimentFilesFolder = isExperimentFilesFolder
        if self.isExperimentFilesFolder:
            absoluteFolderPath = location
        else:
            absoluteFolderPath = os.path.join(location, folderName)
        self.dataFilePaths = []
        self.dataFileDirectories = []
        self.numFiles = 0
        for dirname, _, files in os.walk(absoluteFolderPath):
            for filename in sorted(files):
                if SETTINGS.filters.useIncludesFile and \
                        not SETTINGS.filters.useExcludesFile:
                    if not FolderModel.MatchesIncludes(filename):
                        logger.debug("Ignoring %s, not matching includes."
                                     % filename)
                        continue
                elif not SETTINGS.filters.useIncludesFile and \
                        SETTINGS.filters.useExcludesFile:
                    if FolderModel.MatchesExcludes(filename):
                        logger.debug("Ignoring %s, matching excludes."
                                     % filename)
                        continue
                elif SETTINGS.filters.useIncludesFile and \
                        SETTINGS.filters.useExcludesFile:
                    if FolderModel.MatchesExcludes(filename) and \
                            not FolderModel.MatchesIncludes(filename):
                        logger.debug("Ignoring %s, matching excludes "
                                     "and not matching includes."
                                     % filename)
                        continue
                self.numFiles += 1
                self.dataFilePaths.append(os.path.join(dirname, filename))
                self.dataFileDirectories\
                    .append(os.path.relpath(dirname, absoluteFolderPath))
            if self.isExperimentFilesFolder:
                break
        for i in range(0, len(self.dataFileDirectories)):
            if self.dataFileDirectories[i] == ".":
                self.dataFileDirectories[i] = ""
            self.dataFileDirectories[i] = \
                self.dataFileDirectories[i].replace("\\", "/")
        self.created = ""
        self._experimentTitle = ""
        self.group = None
        self.experimentTitleSetManually = False
        self.status = "0 of %d files uploaded" % (self.numFiles,)
        self.userFolderName = userFolderName
        self.groupFolderName = groupFolderName
        self.owner = owner

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

    def __hash__(self):
        """
        Required to be able to use folderModel as a dictionary key
        in FoldersController
        """
        return hash(self.dataViewId)

    def __eq__(self, other):
        """
        Required to be able to use folderModel as a dictionary key
        in FoldersController
        """
        return self.dataViewId == other.dataViewId

    def SetDataFileUploaded(self, dataFileIndex, uploaded):
        """
        Set a DataFile's upload status

        Used to update the number of files uploaded per folder
        displayed in the Status column of the Folders view.
        """
        self.dataFileUploaded[dataFileIndex] = uploaded
        self.numFilesUploaded = sum(self.dataFileUploaded)
        self.status = "%d of %d files uploaded" % (self.numFilesUploaded,
                                                   self.numFiles)

    def GetDataFilePath(self, dataFileIndex):
        """
        Get the absolute path to a file within this folder's root directory
        which is os.path.join(self.location, self.folderName)
        """
        return self.dataFilePaths[dataFileIndex]

    def GetDataFileRelPath(self, dataFileIndex):
        """
        Get the path to a file relative to the folder's root directory
        which is os.path.join(self.location, self.folderName)
        """
        return os.path.relpath(self.GetDataFilePath(dataFileIndex),
                               SETTINGS.general.dataDirectory)

    def GetDataFileDirectory(self, dataFileIndex):
        """
        Get the relative path to a file's subdirectory relative to the
        folder's root directory which is
        os.path.join(self.location, self.folderName)
        """
        return self.dataFileDirectories[dataFileIndex]

    def GetDataFileName(self, dataFileIndex):
        """
        Return a file's filename
        """
        return os.path.basename(self.dataFilePaths[dataFileIndex])

    def GetDataFileSize(self, dataFileIndex):
        """
        Return a file's size on disk
        """
        return os.stat(self.GetDataFilePath(dataFileIndex)).st_size

    def GetDataFileCreatedTime(self, dataFileIndex):
        """
        Return a file's created time on disk
        """
        absoluteFilePath = self.GetDataFilePath(dataFileIndex)
        try:
            createdTimeIsoString = datetime.fromtimestamp(
                os.stat(absoluteFilePath).st_ctime).isoformat()
            return createdTimeIsoString
        except:
            logger.error(traceback.format_exc())
            return None

    def GetDataFileModifiedTime(self, dataFileIndex):
        """
        Return a file's modified time on disk
        """
        absoluteFilePath = self.GetDataFilePath(dataFileIndex)
        try:
            modifiedTimeIsoString = datetime.fromtimestamp(
                os.stat(absoluteFilePath).st_mtime).isoformat()
            return modifiedTimeIsoString
        except:
            logger.error(traceback.format_exc())
            return None

    def GetRelPath(self):
        """
        Return the relative path of the folder, relative to the root
        data directory configured in MyData's settings
        """
        if self.isExperimentFilesFolder:
            return os.path.relpath(self.location,
                                   SETTINGS.general.dataDirectory)
        else:
            return os.path.join(
                os.path.relpath(self.location, SETTINGS.general.dataDirectory),
                self.folderName)

    def GetNumFiles(self):
        """
        Return total number of files in this folder
        """
        return self.numFiles

    def GetValueForKey(self, key):
        """
        Used in the data view model to look up a value from a column key
        """
        if key.startswith("owner."):
            ownerKey = key.split("owner.")[1]
            return self.owner.GetValueForKey(ownerKey) if self.owner else None
        elif key.startswith("group."):
            groupKey = key.split("group.")[1]
            return self.group.GetValueForKey(groupKey) if self.group else None
        return getattr(self, key)

    def SetCreatedDate(self):
        """
        Set created date
        """
        if self.isExperimentFilesFolder:
            absoluteFolderPath = self.location
        else:
            absoluteFolderPath = os.path.join(self.location, self.folderName)
        self.created = datetime.fromtimestamp(
            os.stat(absoluteFolderPath).st_ctime)\
            .strftime('%Y-%m-%d')

    @property
    def experimentTitle(self):
        """
        Get MyTardis experiment title associated with this folder
        """
        return self._experimentTitle

    @experimentTitle.setter
    def experimentTitle(self, title):
        """
        Set MyTardis experiment title associated with this folder
        """
        self._experimentTitle = title
        self.experimentTitleSetManually = True

    @staticmethod
    def MatchesIncludes(filename):
        """
        Return True if file matches at least one pattern in the includes
        file.
        """
        match = False
        with open(SETTINGS.filters.includesFile, 'r') as includesFile:
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

    @staticmethod
    def MatchesExcludes(filename):
        """
        Return True if file matches at least one pattern in the excludes
        file.
        """
        match = False
        with open(SETTINGS.filters.excludesFile, 'r') as excludesFile:
            for glob in excludesFile.readlines():
                glob = glob.decode('utf-8').strip()
                if glob == "":
                    continue
                if glob.startswith(";"):
                    continue
                if glob.startswith("#"):
                    continue
                match = match or fnmatch(filename, glob)
        return match

    def FileIsTooNewToUpload(self, dataFileIndex):
        """
        Check whether this file's upload should be skipped because it has been
        modified too recently and might require further local modifications
        before its upload.
        """
        if SETTINGS.filters.ignoreNewFiles:
            absoluteFilePath = self.GetDataFilePath(dataFileIndex)
            return (time.time() - os.path.getmtime(absoluteFilePath)) <= \
                (SETTINGS.filters.ignoreNewFilesMinutes * 60)
        else:
            return False

    def CalculateMd5Sum(self, dataFileIndex, progressCallback=None,
                        canceledCallback=None):
        """
        Calculate MD5 checksum.
        """
        absoluteFilePath = self.GetDataFilePath(dataFileIndex)
        fileSize = self.GetDataFileSize(dataFileIndex)
        md5 = hashlib.md5()

        defaultChunkSize = 128 * 1024
        maxChunkSize = 16 * 1024 * 1024
        chunkSize = defaultChunkSize
        while (fileSize / chunkSize) > 50 and chunkSize < maxChunkSize:
            chunkSize *= 2
        bytesProcessed = 0
        with open(absoluteFilePath, 'rb') as fileHandle:
            # Note that the iter() func needs an empty byte string
            # for the returned iterator to halt at EOF, since read()
            # returns b'' (not just '').
            for chunk in iter(lambda: fileHandle.read(chunkSize), b''):
                if canceledCallback():
                    logger.debug("Aborting MD5 calculation for "
                                 "%s" % absoluteFilePath)
                    return None
                md5.update(chunk)
                bytesProcessed += len(chunk)
                del chunk
                if progressCallback:
                    progressCallback(bytesProcessed)
        return md5.hexdigest()

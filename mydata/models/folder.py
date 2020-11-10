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
    def __init__(self, dataViewId, folderName, location, userFolderName,
                 groupFolderName, owner, group=None,
                 isExperimentFilesFolder=False):

        self.dataViewFields = dict(
            dataViewId=dataViewId,
            folderName=folderName,
            location=location,
            created="",
            experimentTitle="",
            status="0 of 0 files uploaded",
            owner=owner,
            group=group)

        # If there are files in the top-level of an Experiment folder, not
        # within any dataset folder, then we create a special dataset to
        # collect these files:
        self.isExperimentFilesFolder = isExperimentFilesFolder

        self.dataFilePaths = dict(
            files=[],
            directories=[],
            uploaded=[])
        self.PopulateDataFilePaths()

        self.userFolderName = userFolderName
        self.groupFolderName = groupFolderName

        self.datasetModel = None
        self.experimentModel = None

    def PopulateDataFilePaths(self):
        """
        Populate data file paths within folder object
        """
        if self.isExperimentFilesFolder:
            absoluteFolderPath = self.location
        else:
            absoluteFolderPath = os.path.join(self.location, self.folderName)

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
                self.dataFilePaths['files'].append(
                    os.path.join(dirname, filename))
                self.dataFilePaths['directories']\
                    .append(os.path.relpath(dirname, absoluteFolderPath))
                self.dataFilePaths['uploaded'].append(False)
            if self.isExperimentFilesFolder:
                break
        self.ConvertSubdirectoriesToMyTardisFormat()
        self.dataViewFields['status'] = \
            "0 of %d files uploaded" % self.numFiles

    def ConvertSubdirectoriesToMyTardisFormat(self):
        """
        When we write a subdirectory path into the directory field of a
        MyTardis DataFile record, we use forward slashes, and use an
        empty string (rather than ".") to indicate that the file is in
        the dataset's top-level directory
        """
        for i in range(0, len(self.dataFilePaths['directories'])):
            if self.dataFilePaths['directories'][i] == ".":
                self.dataFilePaths['directories'][i] = ""
            self.dataFilePaths['directories'][i] = \
                self.dataFilePaths['directories'][i].replace("\\", "/")

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
        self.dataFilePaths['uploaded'][dataFileIndex] = uploaded
        numFilesUploaded = sum(self.dataFilePaths['uploaded'])
        self.dataViewFields['status'] = \
            "%d of %d files uploaded" % (numFilesUploaded,
                                         self.numFiles)

    def GetDataFilePath(self, dataFileIndex):
        """
        Get the absolute path to a file within this folder's root directory
        which is os.path.join(self.location, self.folderName)
        """
        return self.dataFilePaths['files'][dataFileIndex]

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
        return self.dataFilePaths['directories'][dataFileIndex]

    def GetDataFileName(self, dataFileIndex):
        """
        Return a file's filename
        """
        return os.path.basename(self.dataFilePaths['files'][dataFileIndex])

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
            relpath = os.path.relpath(
                self.location, SETTINGS.general.dataDirectory)
        else:
            relpath = os.path.join(
                os.path.relpath(self.location, SETTINGS.general.dataDirectory),
                self.folderName)
        return relpath

    @property
    def numFiles(self):
        """
        Return total number of files in this folder
        """
        return len(self.dataFilePaths['files'])

    def GetValueForKey(self, key):
        """
        Used in the data view model to look up a value from a column key
        """
        if key.startswith("owner."):
            ownerKey = key.split("owner.")[1]
            return self.owner.GetValueForKey(ownerKey) if self.owner else None
        if key.startswith("group."):
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
        self.dataViewFields['created'] = datetime.fromtimestamp(
            os.stat(absoluteFolderPath).st_ctime)\
            .strftime('%Y-%m-%d')

    @property
    def experimentTitle(self):
        """
        Get MyTardis experiment title associated with this folder
        """
        return self.dataViewFields['experimentTitle']

    @experimentTitle.setter
    def experimentTitle(self, title):
        """
        Set MyTardis experiment title associated with this folder
        """
        self.dataViewFields['experimentTitle'] = title

    @staticmethod
    def MatchesPatterns(filename, includesOrExcludesFile):
        """
        Return True if file matches at least one pattern in the includes
        or excludes file.
        """
        match = False
        with open(includesOrExcludesFile, 'r') as patternsFile:
            for glob in patternsFile.readlines():
                glob = glob.strip()
                if glob == "":
                    continue
                if glob.startswith(";"):
                    continue
                if glob.startswith("#"):
                    continue
                match = match or fnmatch(filename, glob)
        return match

    @staticmethod
    def MatchesIncludes(filename):
        """
        Return True if file matches at least one pattern in the includes
        file.
        """
        return FolderModel.MatchesPatterns(
            filename, SETTINGS.filters.includesFile)

    @staticmethod
    def MatchesExcludes(filename):
        """
        Return True if file matches at least one pattern in the excludes
        file.
        """
        return FolderModel.MatchesPatterns(
            filename, SETTINGS.filters.excludesFile)

    def FileIsTooNewToUpload(self, dataFileIndex):
        """
        Check whether this file's upload should be skipped because it has been
        modified too recently and might require further local modifications
        before its upload.
        """
        if SETTINGS.filters.ignoreNewFiles:
            absoluteFilePath = self.GetDataFilePath(dataFileIndex)
            tooNew = (time.time() - os.path.getmtime(absoluteFilePath)) <= \
                (SETTINGS.filters.ignoreNewFilesMinutes * 60)
        else:
            tooNew = False
        return tooNew

    def CalculateMd5Sum(self, dataFileIndex, progressCallback=None,
                        canceledCallback=None):
        """
        Calculate MD5 checksum.
        """
        absoluteFilePath = self.GetDataFilePath(dataFileIndex)
        fileSize = self.GetDataFileSize(dataFileIndex)
        md5 = hashlib.md5()

        defaultChunkSize = 128 * 1024
        maxChunkSize = 32 * 1024 * 1024
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
                    logger.debug("Aborting MD5 calculation for %s" % absoluteFilePath)
                    return None
                md5.update(chunk)
                bytesProcessed += len(chunk)
                del chunk
                if progressCallback:
                    progressCallback(bytesProcessed)
        return md5.hexdigest()

    def ResetCounts(self):
        """
        Reset counts of uploaded files etc.
        """
        self.dataFilePaths['uploaded'] = []
        for _ in range(0, self.numFiles):
            self.dataFilePaths['uploaded'].append(False)

    @property
    def dataViewId(self):
        """
        The row index in MyData's Folders view
        """
        return self.dataViewFields['dataViewId']

    @property
    def folderName(self):
        """
        The folder name, displayed in the Folder (dataset)
        column of MyData's Folders view
        """
        return self.dataViewFields['folderName']

    @property
    def location(self):
        """
        The folder location, displayed in the Location
        column of MyData's Folders view
        """
        return self.dataViewFields['location']

    @property
    def created(self):
        """
        The folder's created date/time stamp, displayed
        in the Created column of MyData's Folders view
        """
        return self.dataViewFields['created']

    @property
    def status(self):
        """
        The folder's upload status, displayed in the
        Status column of MyData's Folders view
        """
        return self.dataViewFields['status']

    @property
    def owner(self):
        """
        The folder's primary owner, i.e. which user should
        be granted access in the ObjectACL), displayed in
        the Owner column of MyData's Folders view
        """
        return self.dataViewFields['owner']

    @property
    def group(self):
        """
        The group which this folder will be granted access to
        via its ObjectACL, displayed in the Group column of
        MyData's Folders view
        """
        return self.dataViewFields['group']

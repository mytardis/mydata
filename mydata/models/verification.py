"""
Model for datafile verification / lookup.
"""


# pylint: disable=invalid-name
# pylint: disable=too-few-public-methods
class VerificationStatus(object):
    """
    Enumerated data type for verification states.
    """
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

    # Missing datafile objects (replicas) on server:
    FOUND_UNVERIFIED_NO_DFOS = 6

    # An unverified DFO (replica) was created previously, but the file
    # can't be found on the staging server:
    NOT_FOUND_ON_STAGING = 7

    # Verification failed, should upload file, unless the failure
    # was so serious (e.g. no network) that we need to abort everything.
    FAILED = 8


# pylint: disable=too-many-instance-attributes
class VerificationModel(object):
    """
    Model for datafile verification / lookup.
    """
    def __init__(self, dataViewId, folderModel, dataFileIndex):
        self.dataViewId = dataViewId
        self.folderModelId = folderModel.GetDataViewId()
        self.folder = folderModel.GetFolder()
        self.subdirectory = folderModel.GetDataFileDirectory(dataFileIndex)
        self.dataFileIndex = dataFileIndex
        self.filename = folderModel.GetDataFileName(dataFileIndex)
        self.message = ""
        self.status = VerificationStatus.NOT_STARTED
        self.complete = False

    def GetDataViewId(self):
        """
        Returns data view ID.
        """
        return self.dataViewId

    def GetFilename(self):
        """
        Returns filename.
        """
        return self.filename

    def GetSubdirectory(self):
        """
        Returns subdirectory.
        """
        return self.subdirectory

    def GetStatus(self):
        """
        Returns status.
        """
        return self.status

    def SetComplete(self, complete=True):
        """
        Set this to True when complete.
        """
        self.complete = complete

    def GetComplete(self):
        """
        Returns True if complete.
        """
        return self.complete

    def SetStatus(self, status):
        """
        Used to set status.
        """
        self.status = status

    def GetMessage(self):
        """
        Get message.
        """
        return self.message

    def SetMessage(self, message):
        """
        Set message.
        """
        self.message = message

    def GetValueForKey(self, key):
        """
        Get value for key.
        """
        return self.__dict__[key]

    def GetFolderModelId(self):
        """
        Get folder model ID.
        """
        return self.folderModelId

    def GetFolder(self):
        """
        Get folder.
        """
        return self.folder

    def GetDataFileIndex(self):
        """
        Get datafile index.
        """
        return self.dataFileIndex

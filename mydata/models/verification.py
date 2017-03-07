"""
Model for datafile verification / lookup.
"""


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

    # Found unverified DataFile record, but we're using POST, not staged
    # uploads, so we can't retry without triggering a Duplicate Key error:
    FOUND_UNVERIFIED_UNSTAGED = 4

    # Finished uploading to staging, waiting
    # for MyTardis to verify (don't re-upload):
    FOUND_UNVERIFIED_FULL_SIZE = 5

    # Partially uploaded to staging, need to resume upload or re-upload:
    FOUND_UNVERIFIED_NOT_FULL_SIZE = 6

    # Missing datafile objects (replicas) on server:
    FOUND_UNVERIFIED_NO_DFOS = 7

    # An unverified DFO (replica) was created previously, but the file
    # can't be found on the staging server:
    NOT_FOUND_ON_STAGING = 8

    # Verification failed, should upload file, unless the failure
    # was so serious (e.g. no network) that we need to abort everything.
    FAILED = 9


class VerificationModel(object):
    """
    Model for datafile verification / lookup.
    """
    def __init__(self, dataViewId, folderModel, dataFileIndex):
        self.dataViewId = dataViewId
        self.folderModelId = folderModel.dataViewId
        self.folderName = folderModel.folderName
        self.subdirectory = folderModel.GetDataFileDirectory(dataFileIndex)
        self.dataFileIndex = dataFileIndex
        self.filename = folderModel.GetDataFileName(dataFileIndex)
        self.message = ""
        self.status = VerificationStatus.NOT_STARTED
        self.complete = False

        # If during verification, it has been determined that an
        # unverified DataFile exists on the server for this file,
        # its DataFileModel object will be recorded:
        self.existingUnverifiedDatafile = None

    def GetValueForKey(self, key):
        """
        Return value of field from the VerificationModel
        to display in the Verifications view
        """
        return getattr(self, key)

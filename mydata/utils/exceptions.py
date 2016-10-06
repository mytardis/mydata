"""
Custom exceptions to raise within MyData.
"""


class DuplicateKey(Exception):
    """
    Duplicate key exception.
    """
    def __init__(self, message):
        super(DuplicateKey, self).__init__(message)


class MultipleObjectsReturned(Exception):
    """
    Multiple objects returned exception.
    """
    def __init__(self, message, url=None, response=None):
        super(MultipleObjectsReturned, self).__init__(message)

        self.url = url
        self.response = response

    def GetUrl(self):
        """
        Returns URL
        """
        return self.url

    def GetResponse(self):
        """
        Returns response
        """
        return self.response


class DoesNotExist(Exception):
    """
    Does not exist exception.
    """
    def __init__(self, message, url=None, response=None, modelClass=None):
        super(DoesNotExist, self).__init__(message)

        self.url = url
        self.response = response
        self.modelClass = modelClass

    def GetUrl(self):
        """
        Returns URL
        """
        return self.url

    def GetResponse(self):
        """
        Returns response
        """
        return self.response

    def GetModelClass(self):
        """
        Returns model class.
        """
        return self.modelClass


class Unauthorized(Exception):
    """
    Unauthorized exception.
    """
    def __init__(self, message, url=None, response=None):
        super(Unauthorized, self).__init__(message)

        self.url = url
        self.response = response

    def GetUrl(self):
        """
        Returns URL
        """
        return self.url

    def GetResponse(self):
        """
        Returns response
        """
        return self.response


class InternalServerError(Exception):
    """
    Internal server exception.
    """
    def __init__(self, message, url=None, response=None):
        super(InternalServerError, self).__init__(message)

        self.url = url
        self.response = response

    def GetUrl(self):
        """
        Returns URL
        """
        return self.url

    def GetResponse(self):
        """
        Returns response
        """
        return self.response


class SshException(Exception):
    """
    SSH exception.
    """
    def __init__(self, message, returncode=None):
        super(SshException, self).__init__(message)
        self.returncode = returncode


class StagingHostRefusedSshConnection(SshException):
    """
    Staging host refused SSH connection exception.
    """
    def __init__(self, message):
        super(StagingHostRefusedSshConnection, self).__init__(message)


class StagingHostSshPermissionDenied(SshException):
    """
    Staging host permission denied exception.
    """
    def __init__(self, message):
        super(StagingHostSshPermissionDenied, self).__init__(message)


class SshControlMasterLimit(SshException):
    """
    Reached max number of connections (or attempted connections)
    in SSH ControlMaster (Mac OS X only).
    This usually means there is a critical problem with SSHing
    to the specified staging host.
    """
    def __init__(self, message):
        super(SshControlMasterLimit, self).__init__(message)


class ScpException(SshException):
    """
    SCP exception.
    """
    def __init__(self, message, command=None, returncode=None):
        super(ScpException, self).__init__(message)
        self.command = command
        self.returncode = returncode


class NoActiveNetworkInterface(Exception):
    """
    No active network interface exception.
    """
    def __init__(self, message):
        super(NoActiveNetworkInterface, self).__init__(message)


class BrokenPipe(Exception):
    """
    Broken pipe exception.
    """
    def __init__(self, message):
        super(BrokenPipe, self).__init__(message)


class IncompatibleMyTardisVersion(Exception):
    """
    Incompatible MyTardis version exception.
    """
    def __init__(self, message):
        super(IncompatibleMyTardisVersion, self).__init__(message)


class PrivateKeyDoesNotExist(Exception):
    """
    Private key does not exist exception.
    """
    def __init__(self, message):
        super(PrivateKeyDoesNotExist, self).__init__(message)


class InvalidFolderStructure(Exception):
    """
    Invalid folder structure exception.
    """
    def __init__(self, message):
        super(InvalidFolderStructure, self).__init__(message)


class MissingMyDataAppOnMyTardisServer(Exception):
    """
    Missing MyData app on MyTardis server exception.
    """
    def __init__(self, message):
        super(MissingMyDataAppOnMyTardisServer, self).__init__(message)


class StorageBoxAttributeNotFound(Exception):
    """
    Storage box attribute not found exception.
    """
    def __init__(self, storageBox, key):
        message = "Key '%s' not found in attributes for storage box '%s'" \
            % (key, storageBox.GetName())
        super(StorageBoxAttributeNotFound, self).__init__(message)


class StorageBoxOptionNotFound(Exception):
    """
    Storage box option not found exception.
    """
    def __init__(self, storageBox, key):
        message = "Key '%s' not found in options for storage box '%s'" \
            % (key, storageBox.GetName())
        super(StorageBoxOptionNotFound, self).__init__(message)


class FileNotFoundOnStaging(Exception):
    """
    While attempting to measure how many bytes of an unverified file have been
    uploaded to staging, MyData determined that the file does not yet exist on
    staging.
    """
    def __init__(self, remoteFilePath):
        message = "No such file or directory: %s" % remoteFilePath
        super(FileNotFoundOnStaging, self).__init__(message)

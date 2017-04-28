"""
Custom exceptions to raise within MyData.
"""


class DuplicateKey(Exception):
    """
    Duplicate key exception.
    """


class HttpException(Exception):
    """
    Base class for deriving HTTP related exception classes from.
    """
    def __init__(self, message, response=None):
        super(HttpException, self).__init__(message)
        self.response = response

    def GetResponse(self):
        """
        Returns response
        """
        return self.response


class MultipleObjectsReturned(HttpException):
    """
    Multiple objects returned exception.
    """


class DoesNotExist(HttpException):
    """
    Does not exist exception. This could be raised when an HTTP status code
    of 404 is received, or when a JSON list expected to return one object
    returns zero objects.
    """
    def __init__(self, message, response=None, modelClass=None):
        super(DoesNotExist, self).__init__(message, response)
        self.modelClass = modelClass

    def GetModelClass(self):
        """
        Returns model class.
        """
        return self.modelClass


class Unauthorized(HttpException):
    """
    Unauthorized exception (HTTP status: 403).
    """


class InternalServerError(HttpException):
    """
    Internal server exception (HTTP status: 500).
    """


class BadGateway(HttpException):
    """
    BadGateway exception (HTTP status: 502).
    """


class ServiceUnavailable(HttpException):
    """
    Service unavailable exception (HTTP status: 503).
    """


class GatewayTimeout(HttpException):
    """
    Gateway timeout exception (HTTP status: 504).
    """


class SshException(Exception):
    """
    SSH exception.
    """
    def __init__(self, message, returncode=None):
        super(SshException, self).__init__(message)
        self.returncode = returncode


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


class BrokenPipe(Exception):
    """
    Broken pipe exception.
    """


class PrivateKeyDoesNotExist(Exception):
    """
    Private key does not exist exception.
    """


class InvalidFolderStructure(Exception):
    """
    Invalid folder structure exception.
    """


class MissingMyDataAppOnMyTardisServer(Exception):
    """
    Missing MyData app on MyTardis server exception.
    """


class MissingMyDataReplicaApiEndpoint(Exception):
    """
    Missing /api/v1/mydata_replica/ endpoint on MyTardis server exception.
    """


class StorageBoxAttributeNotFound(Exception):
    """
    Storage box attribute not found exception.
    """
    def __init__(self, storageBox, key):
        message = "Key '%s' not found in attributes for storage box '%s'" \
            % (key, storageBox.name)
        super(StorageBoxAttributeNotFound, self).__init__(message)


class StorageBoxOptionNotFound(Exception):
    """
    Storage box option not found exception.
    """
    def __init__(self, storageBox, key):
        message = "Key '%s' not found in options for storage box '%s'" \
            % (key, storageBox.name)
        super(StorageBoxOptionNotFound, self).__init__(message)


class UserAbortedSettingsValidation(Exception):
    """
    User aborted settings validation by pressing the Stop button
    on the main window's toolbar.
    """
    def __init__(self, setStatusMessage):
        message = "Settings validation aborted."
        if setStatusMessage:
            setStatusMessage(message)
        super(UserAbortedSettingsValidation, self).__init__(message)


class InvalidSettings(Exception):
    """
    Invalid settings were found by
    mydata.models.settings.validation.ValidateSettings
    """
    def __init__(self, message, field="", suggestion=None):
        self.field = field
        self.suggestion = suggestion
        super(InvalidSettings, self).__init__(message)

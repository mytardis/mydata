"""
Custom exceptions to raise within MyData.
"""


class DuplicateKey(Exception):
    """
    Duplicate key exception.
    """


class MultipleObjectsReturned(Exception):
    """
    Multiple objects returned exception.
    """


class DoesNotExist(Exception):
    """
    Does not exist exception. Raised when when a JSON list
    expected to return one object returns zero objects.
    """
    def __init__(self, message, response=None, modelClass=None):
        super(DoesNotExist, self).__init__(message, response)
        self.modelClass = modelClass

    def GetModelClass(self):
        """
        Returns model class.
        """
        return self.modelClass


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
        self.key = key
        super(StorageBoxAttributeNotFound, self).__init__(message)


class StorageBoxOptionNotFound(Exception):
    """
    Storage box option not found exception.
    """
    def __init__(self, storageBox, key):
        message = "Key '%s' not found in options for storage box '%s'" \
            % (key, storageBox.name)
        super(StorageBoxOptionNotFound, self).__init__(message)


class UserAborted(Exception):
    """
    User aborted by pressing the Stop button
    on the main window's toolbar.
    """


class InvalidSettings(Exception):
    """
    Invalid settings were found by
    mydata.models.settings.validation.ValidateSettings
    """
    def __init__(self, message, field="", suggestion=None):
        self.field = field
        self.suggestion = suggestion
        super(InvalidSettings, self).__init__(message)

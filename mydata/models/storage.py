"""
Model class for MyTardis API v1's StorageBoxResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

from mydata.utils import UnderscoreToCamelcase


# pylint: disable=too-many-instance-attributes
class StorageBox(object):
    """
    Model class for MyTardis API v1's StorageBoxResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    def __init__(self, storageBoxJson):
        self.json = storageBoxJson
        self.storageBoxId = None
        self.djangoStorageClass = None
        self.maxSize = None
        self.status = None
        self.name = None
        self.description = None
        self.masterBox = None
        self.options = []
        self.attributes = []
        if storageBoxJson is not None:
            for key in storageBoxJson:
                attr = UnderscoreToCamelcase(key)
                if attr == "id":
                    attr = "storageBoxId"
                if hasattr(self, attr):
                    self.__dict__[attr] = storageBoxJson[key]
            self.options = []
            for optionJson in storageBoxJson['options']:
                self.options.append(StorageBoxOption(optionJson=optionJson))
            self.attributes = []
            for attrJson in storageBoxJson['attributes']:
                self.attributes.append(StorageBoxAttribute(attrJson=attrJson))

    def GetOptions(self):
        """
        Returns storage box options.
        """
        return self.options

    def GetAttributes(self):
        """
        Returns storage box attributes.
        """
        return self.attributes


class StorageBoxOption(object):
    """
    Model class for MyTardis API v1's StorageBoxOptionResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    def __init__(self, optionJson):
        self.json = optionJson
        self.storageBoxOptionId = None
        self.key = None
        self.value = None
        if optionJson is not None:
            for key in optionJson:
                attr = UnderscoreToCamelcase(key)
                if attr == "id":
                    attr = "storageBoxOptionId"
                if hasattr(self, attr):
                    self.__dict__[attr] = optionJson[key]

    def GetKey(self):
        """
        Return key.
        """
        return self.key

    def GetValue(self):
        """
        Return value.
        """
        return self.value


class StorageBoxAttribute(object):
    """
    Model class for MyTardis API v1's StorageBoxAttributeResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    def __init__(self, attrJson):
        self.json = attrJson
        self.storageBoxAttributeId = None
        self.key = None
        self.value = None
        if attrJson is not None:
            for key in attrJson:
                attr = UnderscoreToCamelcase(key)
                if attr == "id":
                    attr = "storageBoxAttributeId"
                if hasattr(self, attr):
                    self.__dict__[attr] = attrJson[key]

    def GetKey(self):
        """
        Return key.
        """
        return self.key

    def GetValue(self):
        """
        Return value.
        """
        return self.value

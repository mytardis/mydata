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

    def __str__(self):
        return "StorageBox " + self.name

    def __repr__(self):
        return "StorageBox " + self.name

    def GetId(self):
        """
        Returns storage box ID.
        """
        return self.storageBoxId

    def GetDjangoStorageClass(self):
        """
        Returns Django storage class.
        """
        return self.djangoStorageClass

    def GetMaxSize(self):
        """
        Returns maximum size of storage box.
        """
        return self.maxSize

    def GetStatus(self):
        """
        Returns storage box status.
        """
        return self.status

    def GetName(self):
        """
        Returns storage box name.
        """
        return self.name

    def GetDescription(self):
        """
        Returns storage box description.
        """
        return self.description

    def GetMasterBox(self):
        """
        Returns master storage box.
        """
        return self.masterBox

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

    def GetResourceUri(self):
        """
        Returns API resource URI.
        """
        return self.json['resource_uri']

    def GetValueForKey(self, key):
        """
        Get value for key.
        """
        return self.__dict__[key]

    def GetJson(self):
        """
        Get JSON representation.
        """
        return self.json


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

    def __str__(self):
        return "StorageBoxOption %s: %s" % (self.key, self.value)

    def __repr__(self):
        return "StorageBoxOption %s: %s" % (self.key, self.value)

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

    def __str__(self):
        return "StorageBoxAttribute %s: %s" % (self.key, self.value)

    def __repr__(self):
        return "StorageBoxAttribute %s: %s" % (self.key, self.value)

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

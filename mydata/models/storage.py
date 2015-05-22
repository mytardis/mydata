import requests
import json
import urllib

from mydata.logging import logger
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import MultipleObjectsReturned
from mydata.utils.exceptions import IncompatibleMyTardisVersion


class StorageBox():
    def __init__(self, storageBoxJson):
        self.json = storageBoxJson
        self.id = None
        self.django_storage_class = None
        self.max_size = None
        self.status = None
        self.name = None
        self.description = None
        self.master_box = None
        self.options = []
        self.attributes = []
        if storageBoxJson is not None:
            for key in storageBoxJson:
                if hasattr(self, key):
                    self.__dict__[key] = storageBoxJson[key]
            if 'options' not in storageBoxJson:
                message = "Couldn't access storage box options from MyTardis API."
                raise IncompatibleMyTardisVersion(message)
            self.options = []
            for optionJson in storageBoxJson['options']:
                self.options.append(StorageBoxOption(optionJson=optionJson))
            if 'attributes' not in storageBoxJson:
                message = "Couldn't access storage box attributes from MyTardis API."
                raise IncompatibleMyTardisVersion(message)
            self.attributes = []
            for attrJson in storageBoxJson['attributes']:
                self.attributes.append(StorageBoxAttribute(attrJson=attrJson))

    def __str__(self):
        return "StorageBox " + self.name

    def __unicode__(self):
        return "StorageBox " + self.name

    def __repr__(self):
        return "StorageBox " + self.name

    def GetId(self):
        return self.id

    def GetDjangoStorageClass(self):
        return self.django_storage_class

    def GetMaxSize(self):
        return self.max_size

    def GetStatus(self):
        return self.status

    def GetName(self):
        return self.name

    def GetDescription(self):
        return self.description

    def GetMasterBox(self):
        return self.master_box

    def GetOptions(self):
        return self.options

    def GetAttributes(self):
        return self.attributes

    def GetResourceUri(self):
        return self.json['resource_uri']

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetJson(self):
        return self.json


class StorageBoxOption():
    def __init__(self, optionJson):
        self.json = optionJson
        self.id = None
        self.key = None
        self.value = None
        if optionJson is not None:
            for key in optionJson:
                if hasattr(self, key):
                    self.__dict__[key] = optionJson[key]

    def __str__(self):
        return "StorageBoxOption %s: %s" % (self.key, self.value)

    def __unicode__(self):
        return "StorageBoxOption %s: %s" % (self.key, self.value)

    def __repr__(self):
        return "StorageBoxOption %s: %s" % (self.key, self.value)

    def GetKey(self):
        return self.key

    def GetValue(self):
        return self.value


class StorageBoxAttribute():
    def __init__(self, attrJson):
        self.json = attrJson
        self.id = None
        self.key = None
        self.value = None
        if attrJson is not None:
            for key in attrJson:
                if hasattr(self, key):
                    self.__dict__[key] = attrJson[key]

    def __str__(self):
        return "StorageBoxAttribute %s: %s" % (self.key, self.value)

    def __unicode__(self):
        return "StorageBoxAttribute %s: %s" % (self.key, self.value)

    def __repr__(self):
        return "StorageBoxAttribute %s: %s" % (self.key, self.value)

    def GetKey(self):
        return self.key

    def GetValue(self):
        return self.value

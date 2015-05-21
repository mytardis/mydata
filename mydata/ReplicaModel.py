import requests
import json
import urllib

from logger.Logger import logger


class ReplicaModel():

    """
    At the time of writing, the Replica model has been removed from MyTardis
    and replaced with the DataFileObject model.  But MyTardis's API still
    returns JSON labeled as "replicas" within each DataFileResource.
    """

    def __init__(self, settingsModel=None, replicaJson=None):
        self.settingsModel = settingsModel

        self.id = None
        self.uri = None
        self.datafileResourceUri = None
        self.verified = None
        self.last_verified_time = None
        self.created_time = None
        self.json = replicaJson
        self.datafileResourceUri = None

        if replicaJson is not None:
            for key in replicaJson:
                if hasattr(self, key):
                    self.__dict__[key] = replicaJson[key]
            self.datafileResourceUri = replicaJson['datafile']

    def __str__(self):
        return "ReplicaModel " + self.uri

    def __unicode__(self):
        return "ReplicaModel " + self.uri

    def __repr__(self):
        return "ReplicaModel " + self.uri

    def GetId(self):
        return self.id

    def GetUri(self):
        return self.uri

    def GetDataFileResourceUri(self):
        return self.datafileResourceUri

    def IsVerified(self):
        return self.verified

    def GetResourceUri(self):
        return self.json['resource_uri']

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetJson(self):
        return self.json

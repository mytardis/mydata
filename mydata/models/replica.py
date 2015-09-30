"""
Model class for MyTardis API v1's ReplicaResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

from mydata.utils import UnderscoreToCamelcase


# pylint: disable=too-many-instance-attributes
class ReplicaModel(object):
    """
    The Replica model has been removed from MyTardis and replaced by
    the DataFileObject model.  But MyTardis's API still returns
    JSON labeled as "replicas" within each DataFileResource.
    """
    def __init__(self, settingsModel=None, replicaJson=None):
        self.settingsModel = settingsModel

        self.replicaId = None
        self.uri = None
        self.datafileResourceUri = None
        self.verified = None
        self.lastVerifiedTime = None
        self.createdTime = None
        self.json = replicaJson
        self.datafileResourceUri = None

        if replicaJson is not None:
            for key in replicaJson:
                attr = UnderscoreToCamelcase(key)
                if attr == "id":
                    attr = "replicaId"
                if hasattr(self, attr):
                    self.__dict__[attr] = replicaJson[key]
            self.datafileResourceUri = replicaJson['datafile']

    def __str__(self):
        return "ReplicaModel " + self.uri

    def __repr__(self):
        return "ReplicaModel " + self.uri

    def GetId(self):
        """
        Returns primary key
        """
        return self.replicaId

    def GetUri(self):
        """
        Returns the URI field of the DataFileObject represented by
        the ReplicaResource.
        """
        return self.uri

    def GetDataFileResourceUri(self):
        """
        Returns API resource uri for the corresponding DataFile.
        """
        return self.datafileResourceUri

    def IsVerified(self):
        """
        Returns True if the DataFileObject represented by the
        ReplicaResource is verified.
        """
        return self.verified

    def GetResourceUri(self):
        """
        Returns API resource uri for the ReplicaResource.
        """
        return self.json['resource_uri']

    def GetValueForKey(self, key):
        """
        Gets value for key.
        """
        return self.__dict__[key]

    def GetJson(self):
        """
        Returns JSON representation.
        """
        return self.json

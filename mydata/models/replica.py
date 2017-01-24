"""
Model class for MyTardis API v1's ReplicaResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import requests

from mydata.utils import UnderscoreToCamelcase
from mydata.utils.exceptions import MissingMyDataReplicaApiEndpoint


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

    @staticmethod
    def CountBytesUploadedToStaging(settingsModel, dfoId):
        """
        Count bytes uploaded to staging.
        """
        myTardisUrl = settingsModel.GetMyTardisUrl()
        url = "%s/api/v1/mydata_replica/%s/?format=json" \
            % (myTardisUrl, dfoId)
        headers = settingsModel.GetDefaultHeaders()
        response = requests.get(url=url, headers=headers)
        if response.status_code < 200 or response.status_code >= 300:
            if response.status_code == 404:
                message = "Please ask your MyTardis administrator to " \
                    "upgrade mytardis-app-mydata.  The " \
                    "/api/v1/mydata_replica/ endpoint is missing."
                raise MissingMyDataReplicaApiEndpoint(message)
            else:
                message = "Failed to look up DFO ID \"%s\".\n" % dfoId
                message += "HTTP status: %s" % response.status_code
                raise Exception(message)
        dfoJson = response.json()
        return dfoJson['size']

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

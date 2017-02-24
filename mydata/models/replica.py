"""
Model class for MyTardis API v1's ReplicaResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import requests

from ..utils import UnderscoreToCamelcase
from ..utils.exceptions import MissingMyDataReplicaApiEndpoint


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

        if replicaJson is not None:
            for key in replicaJson:
                attr = UnderscoreToCamelcase(key)
                if attr == "id":
                    attr = "replicaId"
                if hasattr(self, attr):
                    self.__dict__[attr] = replicaJson[key]
            self.datafileResourceUri = replicaJson['datafile']

    @staticmethod
    def CountBytesUploadedToStaging(settings, dfoId):
        """
        Count bytes uploaded to staging.
        """
        url = "%s/api/v1/mydata_replica/%s/?format=json" \
            % (settings.general.myTardisUrl, dfoId)
        response = requests.get(url=url, headers=settings.defaultHeaders)
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

    def IsVerified(self):
        """
        Returns True if the DataFileObject represented by the
        ReplicaResource is verified.
        """
        return self.verified

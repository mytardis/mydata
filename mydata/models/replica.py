"""
Model class for MyTardis API v1's ReplicaResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import requests

from ..settings import SETTINGS
from ..utils import UnderscoreToCamelcase
from ..utils.exceptions import MissingMyDataReplicaApiEndpoint
from . import HandleHttpError


class ReplicaModel(object):
    """
    The Replica model has been removed from MyTardis and replaced by
    the DataFileObject model.  But MyTardis's API still returns
    JSON labeled as "replicas" within each DataFileResource.
    """
    def __init__(self, replicaJson=None):
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
    def CountBytesUploadedToStaging(dfoId):
        """
        Count bytes uploaded to staging.
        """
        url = "%s/api/v1/mydata_replica/%s/?format=json" \
            % (SETTINGS.general.myTardisUrl, dfoId)
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
        if response.status_code < 200 or response.status_code >= 300:
            if response.status_code == 404:
                message = "Please ask your MyTardis administrator to " \
                    "upgrade mytardis-app-mydata.  The " \
                    "/api/v1/mydata_replica/ endpoint may be missing."
                raise MissingMyDataReplicaApiEndpoint(message)
            else:
                HandleHttpError(response)
        dfoJson = response.json()
        return dfoJson['size']

    @property
    def dfoId(self):
        """
        Returns primary key of the DataFileObject (DFO),
        (also known as a Replica in the MyTardis API).
        """
        return self.replicaId

    @dfoId.setter
    def dfoId(self, dfoId):
        """
        Sets DFO ID, a.k.a. replica ID.

        Only used in tests.
        """
        self.replicaId = dfoId

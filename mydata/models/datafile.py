"""
Model class for MyTardis API v1's DataFileResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import urllib
import requests

from mydata.logs import logger
from .replica import ReplicaModel
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import MultipleObjectsReturned
from mydata.utils import UnderscoreToCamelcase


# pylint: disable=too-many-instance-attributes
class DataFileModel(object):
    """
    Model class for MyTardis API v1's DataFileResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    def __init__(self, settingsModel, dataset, dataFileJson):
        self.settingsModel = settingsModel
        self.json = dataFileJson
        self.datafileId = None
        self.filename = None
        self.directory = None
        self.size = None
        self.createdTime = None
        self.modificationTime = None
        self.mimetype = None
        self.md5sum = None
        self.sha512sum = None
        self.deleted = None
        self.deletedTime = None
        self.version = None
        self.replicas = []
        self.parameterSets = []
        if dataFileJson is not None:
            for key in dataFileJson:
                attr = UnderscoreToCamelcase(key)
                if attr == "id":
                    attr = "replicaId"
                if hasattr(self, attr):
                    self.__dict__[attr] = dataFileJson[key]
            self.replicas = []
            for replicaJson in dataFileJson['replicas']:
                self.replicas.append(ReplicaModel(replicaJson=replicaJson))
        # This needs to go after self.__dict__[key] = dataFileJson[key]
        # so we get the full dataset model, not just the API resource string:
        self.dataset = dataset

    def __str__(self):
        return "DataFileModel " + self.filename + \
            " - " + self.GetDataset().GetDescription()

    def __repr__(self):
        return "DataFileModel " + self.filename + \
            " - " + self.GetDataset().GetDescription()

    def GetId(self):
        """
        Returns datafile ID.
        """
        return self.datafileId

    def GetDataset(self):
        """
        Returns dataset.
        """
        return self.dataset

    def GetReplicas(self):
        """
        Get replicas.
        """
        return self.replicas

    def IsVerified(self):
        """
        Return True if verified.
        """
        verified = False
        for replica in self.replicas:
            if replica.IsVerified():
                return True
        return verified

    def GetFilename(self):
        """
        Returns filename.
        """
        return self.filename

    def GetDirectory(self):
        """
        Returns directory.
        """
        return self.directory

    def GetResourceUri(self):
        """
        Returns API resource URI.
        """
        return self.json['resource_uri']

    def GetSize(self):
        """
        Returns size.
        """
        return self.size

    def GetValueForKey(self, key):
        """
        Get value for key.
        """
        return self.__dict__[key]

    def GetJson(self):
        """
        Return JSON representation.
        """
        return self.json

    @staticmethod
    def GetDataFile(settingsModel, dataset, filename, directory):
        """
        Lookup datafile by dataset, filename and directory.
        """
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()
        url = myTardisUrl + "/api/v1/mydata_dataset_file/?format=json" + \
            "&dataset__id=" + str(dataset.GetId()) + \
            "&filename=" + urllib.quote(filename) + \
            "&directory=" + urllib.quote(directory)
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey),
            "Content-Type": "application/json",
            "Accept": "application/json"}
        response = requests.get(url=url, headers=headers)
        if response.status_code < 200 or response.status_code >= 300:
            logger.debug("Failed to look up datafile \"%s\" "
                         "in dataset \"%s\"."
                         % (filename, dataset.GetDescription()))
            logger.debug(response.text)
            return None
        dataFilesJson = response.json()
        numDataFilesFound = dataFilesJson['meta']['total_count']
        if numDataFilesFound == 0:
            raise DoesNotExist(
                message="Datafile \"%s\" was not found in MyTardis" % filename,
                url=url, response=response)
        elif numDataFilesFound > 1:
            raise MultipleObjectsReturned(
                message="Multiple datafiles matching %s were found in MyTardis"
                % filename,
                url=url, response=response)
        else:
            return DataFileModel(
                settingsModel=settingsModel,
                dataset=dataset,
                dataFileJson=dataFilesJson['objects'][0])

    @staticmethod
    def Verify(settingsModel, datafileId):
        """
        Verify a datafile via the MyTardis API.
        """
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()
        url = myTardisUrl + "/api/v1/dataset_file/%s/verify/" % datafileId
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey),
            "Content-Type": "application/json",
            "Accept": "application/json"}
        response = requests.get(url=url, headers=headers)
        if response.status_code < 200 or response.status_code >= 300:
            logger.error("Failed to verify datafile id \"%s\" "
                         % datafileId)
            logger.error(response.text)
            return False
        # Returning True doesn't mean that the file has been verified.
        # It just means that the MyTardis API has accepted our verification
        # request without raising an error.  The verification is asynchronous
        # so it might not happen immediately if there is congestion in the
        # Celery queue.
        return True

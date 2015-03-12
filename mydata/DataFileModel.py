import requests
import json
import urllib

from logger.Logger import logger
from DatasetModel import DatasetModel
from ReplicaModel import ReplicaModel
from Exceptions import DoesNotExist
from Exceptions import MultipleObjectsReturned


class DataFileModel():
    def __init__(self, settingsModel, dataset, dataFileJson):
        self.settingsModel = settingsModel
        self.json = dataFileJson
        self.id = None
        self.filename = None
        self.directory = None
        self.size = None
        self.created_time = None
        self.modification_time = None
        self.mimetype = None
        self.md5sum = None
        self.sha512sum = None
        self.deleted = None
        self.deleted_time = None
        self.version = None
        self.replicas = []
        self.parameter_sets = []
        if dataFileJson is not None:
            for key in dataFileJson:
                if hasattr(self, key):
                    self.__dict__[key] = dataFileJson[key]
            self.replicas = []
            for replicaJson in dataFileJson['replicas']:
                self.replicas.append(ReplicaModel(replicaJson=replicaJson))
        # This needs to go after self.__dict__[key] = dataFileJson[key]
        # so we get the full dataset model, not just the API resource string:
        self.dataset = dataset

    def __str__(self):
        return "DataFileModel " + self.filename + \
            " - " + self.GetDataset().GetDescription()

    def __unicode__(self):
        return "DataFileModel " + self.filename + \
            " - " + self.GetDataset().GetDescription()

    def __repr__(self):
        return "DataFileModel " + self.filename + \
            " - " + self.GetDataset().GetDescription()

    def GetId(self):
        return self.id

    def GetDataset(self):
        return self.dataset

    def GetReplicas(self):
        return self.replicas

    def IsVerified(self):
        verified = False
        for replica in self.replicas:
            # Should we also check that it's not in a staging storage box?
            if replica.IsVerified():
                return True
        return verified

    def GetFilename(self):
        return self.filename

    def GetDirectory(self):
        return self.directory

    def GetResourceUri(self):
        return self.json['resource_uri']

    def GetSize(self):
        return self.size

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetJson(self):
        return self.json

    @staticmethod
    def GetDataFile(settingsModel, dataset, filename, directory):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()
        url = myTardisUrl + "/api/v1/dataset_file/?format=json" + \
            "&dataset__id=" + str(dataset.GetId()) + \
            "&filename=" + urllib.quote(filename) + \
            "&directory=" + urllib.quote(directory)
        headers = {"Authorization": "ApiKey " + myTardisUsername + ":" +
                   myTardisApiKey}
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

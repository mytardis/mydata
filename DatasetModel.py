import urllib
import urllib2
import requests
import json
import traceback

from logger.Logger import logger


def countTruesInDictionary(node):
    if isinstance(node, dict):
        return sum([countTruesInDictionary(node[n]) for n in node])
    else:
        return node


class DatasetModel():
    def __init__(self, settingsModel, datasetJson):
        self.settingsModel = settingsModel
        self.json = datasetJson

    def GetJson(self):
        return self.json

    def GetId(self):
        return self.json['id']

    def GetDescription(self):
        return self.json['description']

    def GetResourceUri(self):
        return self.json['resource_uri']

    @staticmethod
    def CreateDatasetIfNecessary(folderModel):
        description = folderModel.GetFolder()

        myTardisUrl = folderModel.settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = folderModel.settingsModel.GetUsername()
        myTardisDefaultUserApiKey = folderModel.settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/dataset/?format=json" + \
            "&experiments__id=" + str(folderModel.GetExperiment().GetId())
        url = url + "&description=" + urllib.quote(description)

        headers = {"Authorization": "ApiKey " + myTardisDefaultUsername + ":" +
                   myTardisDefaultUserApiKey}

        response = requests.get(headers=headers, url=url)
        existingMatchingDatasets = response.json()
        numExistingMatchingDatasets = \
            existingMatchingDatasets['meta']['total_count']
        if numExistingMatchingDatasets == 1:
            logger.debug("Found existing dataset for folder " + description)
        elif numExistingMatchingDatasets > 1:
            logger.debug("WARNING: Found multiple datasets for folder " +
                         description)

        if numExistingMatchingDatasets == 0:
            logger.debug("Creating dataset record for folder: " + description)

            description = folderModel.GetFolder()
            experimentUri = folderModel.GetExperiment().GetResourceUri()
            immutable = False
            datasetJson = {
                "description": description,
                "experiments": [experimentUri],
                "immutable": immutable}
            data = json.dumps(datasetJson)
            headers = {"Authorization": "ApiKey " + myTardisDefaultUsername +
                       ":" + myTardisDefaultUserApiKey,
                       "Content-Type": "application/json",
                       "Accept": "application/json"}
            url = myTardisUrl + "/api/v1/dataset/"
            response = requests.post(headers=headers, url=url, data=data)
            if response.status_code >= 200 and response.status_code < 300:
                newDatasetJson = response.json()
                return DatasetModel(folderModel.settingsModel, newDatasetJson)
            else:
                logger.debug(url)
                logger.debug("response.status_code = " +
                             str(response.status_code))
                return None
        else:
            return DatasetModel(folderModel.settingsModel,
                                existingMatchingDatasets['objects'][0])

    def GetViewUri(self):
        return "dataset/%d" % (self.GetId(),)

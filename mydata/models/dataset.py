import urllib
import urllib2
import requests
import json
import traceback

from logger.Logger import logger
from utils.exceptions import Unauthorized
from utils.exceptions import InternalServerError


class DatasetModel():

    def __init__(self, settingsModel, datasetJson):
        self.settingsModel = settingsModel
        self.json = datasetJson

    def GetJson(self):
        return self.json

    def GetId(self):
        return self.json['id']

    def GetDescription(self):
        try:
            return self.json['description']
        except:
            logger.error("self.json = " + str(self.json))
            logger.error(traceback.format_exc())

    def GetResourceUri(self):
        return self.json['resource_uri']

    @staticmethod
    def CreateDatasetIfNecessary(folderModel):
        description = folderModel.GetFolder()
        settingsModel = folderModel.settingsModel

        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = settingsModel.GetUsername()
        myTardisDefaultUserApiKey = settingsModel.GetApiKey()

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
                "instrument": settingsModel.GetInstrument().GetResourceUri(),
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
                return DatasetModel(settingsModel, newDatasetJson)
            else:
                logger.error(url)
                logger.error("response.status_code = " +
                             str(response.status_code))
                logger.error(response.text)
                if response.status_code == 401:
                    message = "Couldn't create dataset \"%s\" " \
                              "for folder \"%s\"." \
                              % (description, folderModel.GetFolder())
                    message += "\n\n"
                    message += "Please ask your MyTardis administrator to " \
                               "check the permissions of the \"%s\" user " \
                               "account." % myTardisDefaultUsername
                    raise Unauthorized(message)
                elif response.status_code == 500:
                    message = "Couldn't create dataset \"%s\" " \
                              "for folder \"%s\"." \
                              % (description, folderModel.GetFolder())
                    message += "\n\n"
                    message += "An Internal Server Error occurred."
                    message += "\n\n"
                    message += "If running MyTardis in DEBUG mode, " \
                               "more information may be available below. " \
                               "Otherwise, please ask your MyTardis " \
                               "administrator to check in their logs " \
                               "for more information."
                    message += "\n\n"
                    try:
                        message += "ERROR: \"%s\"" \
                            % response.json()['error_message']
                    except:
                        message += response.text
                    raise InternalServerError(message)
                raise Exception(response.text)
        else:
            return DatasetModel(settingsModel,
                                existingMatchingDatasets['objects'][0])

    def GetViewUri(self):
        return "dataset/%d" % (self.GetId(),)

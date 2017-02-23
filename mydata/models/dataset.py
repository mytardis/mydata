"""
Model class for MyTardis API v1's DatasetResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

# pylint: disable=missing-docstring

import urllib
import json
import threading
import requests

from mydata.logs import logger
from mydata.utils.exceptions import Unauthorized
from mydata.utils.exceptions import InternalServerError
from . import HandleHttpError


class DatasetModel(object):
    """
    Client-side model for caching results of querying
    MyTardis's dataset model.
    """
    def __init__(self, settingsModel, datasetJson):
        self.settingsModel = settingsModel
        self.json = datasetJson
        self.datafiles = None
        self.getDatasetFilesThreadingLock = threading.Lock()

    def GetId(self):
        return self.json['id']

    def GetDescription(self):
        return self.json['description']

    def GetResourceUri(self):
        return self.json['resource_uri']

    def GetViewUri(self):
        return "dataset/%d" % (self.GetId(),)

    @staticmethod
    def CreateDatasetIfNecessary(folderModel, testRun=False):
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-locals
        description = folderModel.GetFolder()
        settingsModel = folderModel.settingsModel

        myTardisUsername = settingsModel.general.username
        myTardisUrl = settingsModel.general.myTardisUrl

        experiment = folderModel.GetExperiment()
        if experiment:  # Could be None in test run
            url = myTardisUrl + "/api/v1/dataset/?format=json" + \
                "&experiments__id=" + str(experiment.GetId())
            url = url + "&description=" + \
                urllib.quote(description.encode('utf-8'))
            response = requests.get(headers=settingsModel.defaultHeaders,
                                    url=url)
            if response.status_code != 200:
                HandleHttpError(response)
            existingMatchingDatasets = response.json()
            numExistingMatchingDatasets = \
                existingMatchingDatasets['meta']['total_count']
            if numExistingMatchingDatasets == 1:
                logger.debug("Found existing dataset for folder " + description)
            elif numExistingMatchingDatasets > 1:
                logger.debug("WARNING: Found multiple datasets for folder " +
                             description)
        else:
            numExistingMatchingDatasets = 0
            existingMatchingDatasets = {
                "meta": {
                    "limit": 20,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total_count": 0
                },
                "objects": []
            }

        if numExistingMatchingDatasets == 0:
            logger.debug("Creating dataset record for folder: " + description)

            description = folderModel.GetFolder()
            if experiment:
                experimentUri = experiment.GetResourceUri()
            else:
                experimentUri = None
            immutable = False
            datasetJson = {
                "instrument": settingsModel.instrument.GetResourceUri(),
                "description": description,
                "experiments": [experimentUri],
                "immutable": immutable}
            data = json.dumps(datasetJson)
            url = myTardisUrl + "/api/v1/dataset/"
            if testRun:
                message = "CREATING NEW DATASET FOR FOLDER: %s\n" \
                    "    Description: %s" \
                    % (folderModel.GetRelPath(),
                       description)
                if experiment:  # Could be None in test run.
                    message += "\n    In Experiment: %s/%s" \
                        % (folderModel.settingsModel.general.myTardisUrl,
                           experiment.GetViewUri())
                logger.testrun(message)
                return
            response = requests.post(headers=settingsModel.defaultHeaders,
                                     url=url, data=data)
            if response.status_code == 201:
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
                               "account." % myTardisUsername
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
            existingDatasetJson = \
                existingMatchingDatasets['objects'][0]
            if testRun:
                description = existingDatasetJson['description']
                datasetId = existingDatasetJson['id']
                viewUri = "dataset/%s" % datasetId
                message = "ADDING TO EXISTING DATASET FOR FOLDER: %s\n" \
                    "    URL: %s/%s\n" \
                    "    Description: %s\n" \
                    "    In Experiment: %s/%s" \
                    % (folderModel.GetRelPath(),
                       folderModel.settingsModel.general.myTardisUrl,
                       viewUri,
                       description,
                       folderModel.settingsModel.general.myTardisUrl,
                       folderModel.GetExperiment().GetViewUri())
                logger.testrun(message)
            return DatasetModel(settingsModel,
                                existingMatchingDatasets['objects'][0])

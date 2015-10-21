"""
Model class for MyTardis API v1's DatasetResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

# pylint: disable=missing-docstring

import urllib
import requests
import json
import traceback
import threading

from mydata.logs import logger
from mydata.utils.exceptions import Unauthorized
from mydata.utils.exceptions import InternalServerError


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

    def GetJson(self):
        return self.json

    def GetId(self):
        return self.json['id']

    def GetDescription(self):
        try:
            return self.json['description']
        except:  # pylint: disable=bare-except
            logger.error("self.json = " + str(self.json))
            logger.error(traceback.format_exc())

    def GetResourceUri(self):
        return self.json['resource_uri']

    def GetViewUri(self):
        return "dataset/%d" % (self.GetId(),)

    def GetDataFiles(self):
        if not self.datafiles:
            try:
                self.getDatasetFilesThreadingLock.acquire()
                if self.datafiles:
                    return self.datafiles
                myTardisUrl = self.settingsModel.GetMyTardisUrl()
                myTardisUsername = self.settingsModel.GetUsername()
                myTardisApiKey = self.settingsModel.GetApiKey()

                # limit=0 can still encounter a limit of 1000 unless
                # API_LIMIT_PER_PAGE is set to 0 in MyTardis's settings.py
                limit = 0
                url = "%s/api/v1/dataset/%d/files/?format=json&limit=%d" \
                    % (myTardisUrl, self.GetId(), limit)
                headers = {
                    "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                                       myTardisApiKey)}
                logger.debug(url)
                response = requests.get(headers=headers, url=url)
                if response.status_code >= 200 and response.status_code < 300:
                    from .datafile import DataFileModel
                    self.datafiles = []
                    datafilesJson = response.json()['objects']
                    for datafileJson in datafilesJson:
                        self.datafiles.append(DataFileModel(self.settingsModel,
                                                            self,
                                                            datafileJson))
                    offset = 0
                    while response.json()['meta']['next']:
                        # We should be able to use
                        # response.json()['meta']['next'] in the URL,
                        # instead of manually constructing the next
                        # URL using offset.
                        # But response.json()['meta']['next'] seems to give
                        # the wrong URL for /api/v1/dataset/%d/files/
                        offset += 1
                        url = "%s/api/v1/dataset/%d/files/?format=json" \
                            "&limit=%d&offset=%d" % (myTardisUrl, self.GetId(),
                                                     limit, offset)
                        logger.debug(url)
                        response = requests.get(headers=headers, url=url)
                        if response.status_code >= 200 and \
                                response.status_code < 300:
                            datafilesJson = response.json()['objects']
                            for datafileJson in datafilesJson:
                                self.datafiles\
                                    .append(DataFileModel(self.settingsModel,
                                                          self, datafileJson))
                        else:
                            logger.error(url)
                            logger.error("response.status_code = " +
                                         str(response.status_code))
                            logger.error(response.text)

                else:
                    logger.error(url)
                    logger.error("response.status_code = " +
                                 str(response.status_code))
                    logger.error(response.text)
                    if response.status_code == 401:
                        message = "Couldn't list files for dataset \"%s\". " \
                                  % (self.GetDescription())
                        message += "\n\n"
                        message += "Please ask your MyTardis administrator " \
                                   "to check the permissions of the \"%s\" " \
                                   "user account." % myTardisUsername
                        self.getDatasetFilesThreadingLock.release()
                        raise Unauthorized(message)
                    self.getDatasetFilesThreadingLock.release()
                    raise Exception(response.text)
            finally:
                self.getDatasetFilesThreadingLock.release()
        return self.datafiles

    @staticmethod
    def CreateDatasetIfNecessary(folderModel):
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        description = folderModel.GetFolder()
        settingsModel = folderModel.settingsModel

        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/dataset/?format=json" + \
            "&experiments__id=" + str(folderModel.GetExperiment().GetId())
        url = url + "&description=" + urllib.quote(description)

        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey)}

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
            headers = {
                "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                                   myTardisApiKey),
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
                    except:  # pylint: disable=bare-except
                        message += response.text
                    raise InternalServerError(message)
                raise Exception(response.text)
        else:
            return DatasetModel(settingsModel,
                                existingMatchingDatasets['objects'][0])

import requests
import json
import urllib2

from logger.Logger import logger


class ExperimentModel():
    def __init__(self, settingsModel, experimentJson):
        self.settingsModel = settingsModel
        self.json = experimentJson

    @staticmethod
    def GetExperimentForFolder(folderModel):

        settingsModel = folderModel.GetSettingsModel()
        createdDate = folderModel.GetCreated()
        ownerUsername = folderModel.GetOwner().GetUsername()
        ownerUserId = folderModel.GetOwner().GetJson()['id']

        instrumentName = settingsModel.GetInstrumentName()
        institutionName = settingsModel.GetInstitutionName()
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = settingsModel.GetUsername()
        myTardisDefaultUserApiKey = settingsModel.GetApiKey()

        # First, let's check to see if an experiment already
        # exists for this folder:

        experimentName = instrumentName + " " + createdDate
        expNameEncoded = urllib2.quote(experimentName)
        instrumentNameEncoded = urllib2.quote(instrumentName)
        url = myTardisUrl + "/api/v1/experiment/?format=json" + \
            "&instrument=" + instrumentNameEncoded + \
            "&owner=" + ownerUsername + "&date=" + createdDate
        headers = {"Authorization": "ApiKey " + myTardisDefaultUsername + ":" +
                   myTardisDefaultUserApiKey}
        response = requests.get(url=url, headers=headers)
        numExperimentsFound = 0
        experimentsJson = []
        try:
            experimentsJson = response.json()
            numExperimentsFound = experimentsJson['meta']['total_count']
        except:
            logger.debug(url)
            logger.debug(response.text)
            logger.debug("response.status_code = " + str(response.status_code))
            return None

        # If no matching experiment is found, create one.
        # If one matching experiment is found, return it.
        # If more than one matching experiment is found, raise an exception.

        if numExperimentsFound == 0:
            # If no matching experiment is found, create one:
            logger.debug("Creating experiment for instrument \"" +
                         instrumentName + ", username " + ownerUsername +
                         " and created date " + createdDate)
            experimentJson = {
                "title": experimentName,
                "description": "Instrument: %s\n\n" +
                               "Owner: %s\n\n" +
                               "Data collected: %s" %
                               (instrumentName,
                                ownerUsername,
                                createdDate),
                "institution_name": institutionName,
                "immutable": False,
                "parameter_sets": [{
                    "schema": "http://tardis.edu.au/schemas"
                              "/experimentInstrument",
                    "parameters": [{"name": "instrument",
                                    "value": instrumentName},
                                   {"name": "owner",
                                    "value": ownerUsername},
                                   {"name": "date",
                                    "value": createdDate}]}]}
            headers = {"Authorization": "ApiKey " +
                       myTardisDefaultUsername + ":" +
                       myTardisDefaultUserApiKey,
                       "Content-Type": "application/json",
                       "Accept": "application/json"}
            url = myTardisUrl + "/api/v1/experiment/"
            response = requests.post(headers=headers, url=url,
                                     data=json.dumps(experimentJson))
            try:
                experimentJson = response.json()
            except:
                logger.debug(url)
                logger.debug(response.text)
                logger.debug("response.status_code = " +
                             str(response.status_code))
                return None
            if response.status_code == 201:
                logger.debug("Succeeded in creating experiment for instrument"
                             "\"" + instrumentName + "\" and user " +
                             ownerUsername + " for creation date " +
                             createdDate)

                logger.debug("\nSharing via ObjectACL with username \"" +
                             ownerUsername + "\"...\n")

                objectAclJson = {
                    "pluginId": "django_user",
                    "entityId": str(ownerUserId),
                    "content_object": experimentJson['resource_uri'],
                    "object_id": experimentJson['id'],
                    "aclOwnershipType": 1,
                    "isOwner": True,
                    "canRead": True,
                    "canWrite": True,
                    "canDelete": False,
                    "effectiveDate": None,
                    "expiryDate": None}

                headers = {"Authorization": "ApiKey " +
                           myTardisDefaultUsername + ":" +
                           myTardisDefaultUserApiKey,
                           "Content-Type": "application/json",
                           "Accept": "application/json"}
                url = myTardisUrl + "/api/v1/objectacl/"
                response = requests.post(headers=headers, url=url,
                                         data=json.dumps(objectAclJson))
                if response.status_code == 201:
                    logger.debug("Shared experiment with user " +
                                 ownerUsername + ".")
                else:
                    logger.debug(url)
                    logger.debug(response.text)
                    logger.debug("response.status_code = " +
                                 str(response.status_code))
                    return None
            else:
                logger.debug("Failed to create experiment for instrument " +
                             instrumentName + " and user " + ownerUsername +
                             " for creation date " + createdDate)
                logger.debug(headers)
                logger.debug(url)
                logger.debug(response.text)
                logger.debug("response.status_code = " +
                             str(response.status_code))
                return None
            return ExperimentModel(settingsModel, experimentJson)
        elif numExperimentsFound > 1:
            logger.debug("ERROR: Found multiple experiments matching " +
                         "instrument name and creation date for user 'mmi':\n")
            for expJson in experimentsJson['objects']:
                logger.debug(expJson['title'])
            return None
        else:
            # If one matching experiment is found, return it.
            logger.debug("Found existing experiment for instrument \"" +
                         instrumentName + "\" and user " + ownerUsername +
                         " for creation date " + createdDate)
            return ExperimentModel(settingsModel,
                                   experimentsJson['objects'][0])

    def GetJson(self):
        return self.json

    def GetId(self):
        return self.json['id']

    def GetResourceUri(self):
        return self.json['resource_uri']

    def GetViewUri(self):
        return "experiment/view/%d/" % (self.GetId(),)

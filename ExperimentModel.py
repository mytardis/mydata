import requests
import json
import urllib2

from logger.Logger import logger
from Exceptions import Unauthorized
from Exceptions import DoesNotExist
from Exceptions import MultipleObjectsReturned


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
            if response.status_code == 404:
                message = "Couldn't retrieve experiment \"%s\" " \
                          "for folder \"%s\"." \
                          % (experimentName, folderModel.GetFolder())
                message += "\n\n"
                message += "A 404 (Not Found) error occurred while " \
                           "attempting to retrieve the experiment.\n\n" \
                           "Please ask your MyTardis administrator to " \
                           "check that a User Profile record exists " \
                           "for the \"%s\" user account." \
                           % myTardisDefaultUsername
                raise DoesNotExist(message)
            raise

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
                "description": "Instrument: %s\n\n"
                               "Owner: %s\n\n"
                               "Data collected: %s" %
                               (instrumentName,
                                ownerUsername,
                                createdDate),
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
                if response.status_code == 401:
                    message = "Couldn't create experiment \"%s\" " \
                              "for folder \"%s\"." \
                              % (experimentName, folderModel.GetFolder())
                    message += "\n\n"
                    message += "Please ask your MyTardis administrator to " \
                               "check the permissions of the \"%s\" user " \
                               "account." % myTardisDefaultUsername
                    raise Unauthorized(message)
                elif response.status_code == 404:
                    message = "Couldn't create experiment \"%s\" " \
                              "for folder \"%s\"." \
                              % (experimentName, folderModel.GetFolder())
                    message += "\n\n"
                    message += "A 404 (Not Found) error occurred while " \
                               "attempting to create the experiment.\n\n" \
                               "Please ask your MyTardis administrator to " \
                               "check that a User Profile record exists " \
                               "for the \"%s\" user account." \
                               % myTardisDefaultUsername
                    raise DoesNotExist(message)
                raise
            if response.status_code == 201:
                logger.debug("Succeeded in creating experiment for instrument "
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
                    if response.status_code == 401:
                        message = "Couldn't create ObjectACL for " \
                                  "experiment \"%s\"." % experimentName
                        message += "\n\n"
                        message += "Please ask your MyTardis administrator " \
                                   "to check the permissions of the \"%s\" " \
                                   "user account." % myTardisDefaultUsername
                        raise Unauthorized(message)
                    elif response.status_code == 404:
                        message = "Couldn't create ObjectACL for " \
                                  "experiment \"%s\"." % experimentName
                        message += "\n\n"
                        message += "A 404 (Not Found) error occurred while " \
                                   "attempting to create the ObjectACL.\n\n" \
                                   "Please ask your MyTardis administrator " \
                                   "to check that a User Profile record " \
                                   "exists for the \"%s\" user account." \
                                   % myTardisDefaultUsername
                        raise DoesNotExist(message)
                    raise
            else:
                logger.debug("Failed to create experiment for instrument " +
                             instrumentName + " and user " + ownerUsername +
                             " for creation date " + createdDate)
                logger.debug(headers)
                logger.debug(url)
                logger.debug(response.text)
                logger.debug("response.status_code = " +
                             str(response.status_code))
                if response.status_code == 401:
                    message = "Couldn't create experiment \"%s\" " \
                              "for folder \"%s\"." \
                              % (experimentName, folderModel.GetFolder())
                    message += "\n\n"
                    message += "Please ask your MyTardis administrator to " \
                               "check the permissions of the \"%s\" user " \
                               "account." % myTardisDefaultUsername
                    raise Unauthorized(message)
                elif response.status_code == 404:
                    message = "Couldn't create experiment \"%s\" " \
                              "for folder \"%s\"." \
                              % (experimentName, folderModel.GetFolder())
                    message += "\n\n"
                    message += "A 404 (Not Found) error occurred while " \
                               "attempting to create the experiment.\n\n" \
                               "Please ask your MyTardis administrator to " \
                               "check that a User Profile record exists " \
                               "for the \"%s\" user account." \
                               % myTardisDefaultUsername
                    raise DoesNotExist(message)
                raise
            return ExperimentModel(settingsModel, experimentJson)
        elif numExperimentsFound > 1:
            logger.error("ERROR: Found multiple experiments matching " +
                         "instrument name and creation date for user 'mmi':\n")
            for expJson in experimentsJson['objects']:
                logger.error("\t" + expJson['title'])
            message = "Multiple experiments were found matching " \
                      "instrument \"%s\", owner \"%s\" and date " \
                      "\"%s\" for folder \"%s\"." \
                      % (instrumentName, ownerUsername, createdDate,
                         folderModel.GetFolder())
            message += "\n\n"
            message += "This shouldn't happen.  Please ask your " \
                       "MyTardis administrator to investigate."
            raise MultipleObjectsReturned(message)
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

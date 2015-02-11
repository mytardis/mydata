import requests
import json
import urllib2

from logger.Logger import logger
from Exceptions import Unauthorized
from Exceptions import DoesNotExist
from Exceptions import MultipleObjectsReturned
from UserModel import UserProfileModel
from ObjectAclModel import ObjectAclModel


class ExperimentModel():
    def __init__(self, settingsModel, experimentJson):
        self.settingsModel = settingsModel
        self.json = experimentJson

    @staticmethod
    def GetOrCreateExperimentForFolder(folderModel):
        """
        See also GetExperimentForFolder, CreateExperimentForFolder
        """
        try:
            existingExperiment = \
                ExperimentModel.GetExperimentForFolder(folderModel)
            return existingExperiment
        except DoesNotExist, e:
            if e.GetModelClass() == ExperimentModel:
                return ExperimentModel.CreateExperimentForFolder(folderModel)
            else:
                raise

    @staticmethod
    def GetExperimentForFolder(folderModel):
        """
        See also GetOrCreateExperimentForFolder
        """
        settingsModel = folderModel.GetSettingsModel()
        createdDate = folderModel.GetCreated()
        ownerUsername = folderModel.GetOwner().GetUsername()
        try:
            ownerUserId = folderModel.GetOwner().GetJson()['id']
        except:
            ownerUserId = None

        instrumentName = settingsModel.GetInstrumentName()
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = settingsModel.GetUsername()
        myTardisDefaultUserApiKey = settingsModel.GetApiKey()
        experimentTitle = folderModel.GetExperimentTitle()

        if folderModel.ExperimentTitleSetManually():
            expTitleEncoded = urllib2.quote(experimentTitle)
            instrumentNameEncoded = urllib2.quote(instrumentName)
            url = myTardisUrl + "/api/v1/experiment/?format=json" + \
                "&instrument=" + instrumentNameEncoded + \
                "&owner=" + ownerUsername + "&title=" + expTitleEncoded
        else:
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
                          % (experimentTitle, folderModel.GetFolder())
                message += "\n\n"
                message += "A 404 (Not Found) error occurred while " \
                           "attempting to retrieve the experiment.\n\n" \
                           "Please ask your MyTardis administrator to " \
                           "check that a User Profile record exists " \
                           "for the \"%s\" user account." \
                           % myTardisDefaultUsername
                raise DoesNotExist(message, modelClass=UserProfileModel)
            raise
        if numExperimentsFound == 0:
            if folderModel.ExperimentTitleSetManually():
                message = "Experiment not found for '%s', %s, '%s'" \
                    % (instrumentName, ownerUsername, experimentTitle)
            else:
                message = "Experiment not found for '%s', %s, %s" \
                    % (instrumentName, ownerUsername, createdDate)
            raise DoesNotExist(message, modelClass=ExperimentModel)
        if numExperimentsFound == 1:
            logger.debug("Found existing experiment for instrument \"" +
                         instrumentName + "\" and user " + ownerUsername +
                         " for creation date " + createdDate)
            return ExperimentModel(settingsModel,
                                   experimentsJson['objects'][0])
        elif numExperimentsFound > 1:
            logger.error("ERROR: Found multiple experiments matching " +
                         "instrument name and creation date for user 'mmi':\n")
            for expJson in experimentsJson['objects']:
                logger.error("\t" + expJson['title'])
            if folderModel.ExperimentTitleSetManually():
                message = "Multiple experiments were found matching " \
                          "instrument \"%s\", owner \"%s\" and title " \
                          "\"%s\" for folder \"%s\"." \
                          % (instrumentName, ownerUsername, experimentTitle,
                             folderModel.GetFolder())
            else:
                message = "Multiple experiments were found matching " \
                          "instrument \"%s\", owner \"%s\" and date " \
                          "\"%s\" for folder \"%s\"." \
                          % (instrumentName, ownerUsername, createdDate,
                             folderModel.GetFolder())
            message += "\n\n"
            message += "This shouldn't happen.  Please ask your " \
                       "MyTardis administrator to investigate."
            raise MultipleObjectsReturned(message)

    @staticmethod
    def CreateExperimentForFolder(folderModel):
        settingsModel = folderModel.GetSettingsModel()
        createdDate = folderModel.GetCreated()
        owner = folderModel.GetOwner()
        ownerUsername = folderModel.GetOwner().GetUsername()
        try:
            ownerUserId = folderModel.GetOwner().GetJson()['id']
        except:
            ownerUserId = None

        instrumentName = settingsModel.GetInstrumentName()
        experimentTitle = folderModel.GetExperimentTitle()

        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = settingsModel.GetUsername()
        myTardisDefaultUserApiKey = settingsModel.GetApiKey()

        logger.debug("Creating experiment for instrument \"" +
                     instrumentName + ", username " + ownerUsername +
                     " and created date " + createdDate)
        description = ("Instrument: %s\n\n"
                       "Owner: %s"
                       % (instrumentName, ownerUsername))
        if not folderModel.ExperimentTitleSetManually():
            description += "\n\nData collected: %s" % createdDate
        experimentJson = {
            "title": experimentTitle,
            "description": description,
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
            createdExperimentJson = response.json()
            createdExperiment = ExperimentModel(settingsModel,
                                                createdExperimentJson)
        except:
            logger.debug(url)
            logger.debug(response.text)
            logger.debug("response.status_code = " +
                         str(response.status_code))
            if response.status_code == 401:
                message = "Couldn't create experiment \"%s\" " \
                          "for folder \"%s\"." \
                          % (experimentTitle, folderModel.GetFolder())
                message += "\n\n"
                message += "Please ask your MyTardis administrator to " \
                           "check the permissions of the \"%s\" user " \
                           "account." % myTardisDefaultUsername
                raise Unauthorized(message)
            elif response.status_code == 404:
                message = "Couldn't create experiment \"%s\" " \
                          "for folder \"%s\"." \
                          % (experimentTitle, folderModel.GetFolder())
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

            # Avoid creating a duplicate ObjectACL if the user folder's
            # username matches the facility manager's username.
            # Don't attempt to create an ObjectACL record for an
            # invalid user (without a MyTardis user ID).
            if myTardisDefaultUsername != ownerUsername and \
                    ownerUserId is not None:
                ObjectAclModel.ShareExperimentWithUser(createdExperiment,
                                                       owner)
            if folderModel.GetGroup() is not None:
                ObjectAclModel.ShareExperimentWithGroup(createdExperiment,
                                                        folderModel.GetGroup())
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
                          % (experimentTitle, folderModel.GetFolder())
                message += "\n\n"
                message += "Please ask your MyTardis administrator to " \
                           "check the permissions of the \"%s\" user " \
                           "account." % myTardisDefaultUsername
                raise Unauthorized(message)
            elif response.status_code == 404:
                message = "Couldn't create experiment \"%s\" " \
                          "for folder \"%s\"." \
                          % (experimentTitle, folderModel.GetFolder())
                message += "\n\n"
                message += "A 404 (Not Found) error occurred while " \
                           "attempting to create the experiment.\n\n" \
                           "Please ask your MyTardis administrator to " \
                           "check that a User Profile record exists " \
                           "for the \"%s\" user account." \
                           % myTardisDefaultUsername
                raise DoesNotExist(message)
            raise
        return createdExperiment

    def GetJson(self):
        return self.json

    def GetId(self):
        return self.json['id']

    def GetTitle(self):
        return self.json['title']

    def GetResourceUri(self):
        return self.json['resource_uri']

    def GetViewUri(self):
        return "experiment/view/%d/" % (self.GetId(),)

    def GetSettingsModel(self):
        return self.settingsModel

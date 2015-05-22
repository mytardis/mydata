import requests
import json
import urllib2

from logger.Logger import logger
from utils.exceptions import Unauthorized
from utils.exceptions import DoesNotExist
from utils.exceptions import MultipleObjectsReturned
from .user import UserProfileModel
from .objectacl import ObjectAclModel
from .schema import SchemaModel


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

        uploaderName = settingsModel.GetUploaderModel().GetName()
        uploaderUuid = settingsModel.GetUploaderModel().GetUuid()
        userFolderName = folderModel.GetUserFolderName()
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = settingsModel.GetUsername()
        myTardisDefaultUserApiKey = settingsModel.GetApiKey()
        experimentTitle = folderModel.GetExperimentTitle()

        if folderModel.ExperimentTitleSetManually():
            expTitleEncoded = urllib2.quote(experimentTitle)
            url = myTardisUrl + "/api/v1/mydata_experiment/?format=json" + \
                "&uploader=" + uploaderUuid + \
                "&user_folder_name=" + userFolderName + \
                "&title=" + expTitleEncoded
        else:
            url = myTardisUrl + "/api/v1/mydata_experiment/?format=json" + \
                "&uploader=" + uploaderUuid + \
                "&user_folder_name=" + userFolderName

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
                message = "Failed to confirm existence of experiment \"%s\" " \
                          "for folder \"%s\"." \
                          % (experimentTitle, folderModel.GetFolder())
                message += "\n\n"
                modelClassOfObjectNotFound = None
                try:
                    errorResponse = response.json()
                    if errorResponse['error_message'] == \
                            "UserProfile matching query does not exist.":
                        modelClassOfObjectNotFound = UserProfileModel
                    elif errorResponse['error_message'] == \
                            "Schema matching query does not exist.":
                        modelClassOfObjectNotFound = SchemaModel
                    elif errorResponse['error_message'] == \
                            "Sorry, this request could not be processed. " \
                            "Please try again later.":
                        raise Exception("TASTYPIE_CANNED_ERROR")
                    message += "A 404 (Not Found) error occurred while " \
                               "attempting to retrieve the experiment " \
                               "record:\n\n" \
                               "    %s\n\n" % errorResponse['error_message']
                except:
                    message += "A 404 (Not Found) error occurred while " \
                               "attempting to retrieve the experiment " \
                               "record.  This could be caused by a missing " \
                               "UserProfile record for user \"%s\" or it " \
                               "could be caused by a missing Schema record " \
                               "(see https://github.com/wettenhj/" \
                               "mytardis-app-mydata/blob/master/README.md)" \
                               "\n\n" \
                               "Turning on DEBUG mode on the MyTardis " \
                               "server could help to isolate the problem." \
                               % myTardisDefaultUsername
                if modelClassOfObjectNotFound == UserProfileModel:
                    message += "Please ask your MyTardis administrator to " \
                               "ensure that a User Profile record exists " \
                               "for the \"%s\" user account." \
                               % myTardisDefaultUsername
                elif modelClassOfObjectNotFound == SchemaModel:
                    message += "Please ask your MyTardis administrator to " \
                               "create the experiment metadata schema " \
                               "described in the \"MyTardis Prerequisites\" " \
                               "section of the MyData documentation:\n\n" \
                               "http://mydata.readthedocs.org/en/latest/" \
                               "mytardis-prerequisites.html"
                raise DoesNotExist(message,
                                   modelClass=modelClassOfObjectNotFound)
            raise
        if numExperimentsFound == 0:
            if folderModel.ExperimentTitleSetManually():
                message = "Experiment not found for '%s', %s, '%s'" \
                    % (uploaderName, userFolderName, experimentTitle)
            else:
                message = "Experiment not found for '%s', %s" \
                    % (uploaderName, userFolderName)
            raise DoesNotExist(message, modelClass=ExperimentModel)
        if numExperimentsFound == 1:
            logger.debug("Found existing experiment for uploader \"" +
                         uploaderName + "\" and user folder " + userFolderName)
            return ExperimentModel(settingsModel,
                                   experimentsJson['objects'][0])
        elif numExperimentsFound > 1:
            logger.error("ERROR: Found multiple experiments matching " +
                         "Uploader UUID for user '%s':\n" % userFolderName)
            for expJson in experimentsJson['objects']:
                logger.error("\t" + expJson['title'])
            if folderModel.ExperimentTitleSetManually():
                message = "Multiple experiments were found matching " \
                          "uploader \"%s\", user folder \"%s\" and title " \
                          "\"%s\" for folder \"%s\"." \
                          % (uploaderName, userFolderName, experimentTitle,
                             folderModel.GetFolder())
            else:
                message = "Multiple experiments were found matching " \
                          "uploader \"%s\" and user folder \"%s\" " \
                          "for folder \"%s\"." \
                          % (uploaderName, userFolderName,
                             folderModel.GetFolder())
            message += "\n\n"
            message += "This shouldn't happen.  Please ask your " \
                       "MyTardis administrator to investigate."
            raise MultipleObjectsReturned(message)

    @staticmethod
    def CreateExperimentForFolder(folderModel):
        settingsModel = folderModel.GetSettingsModel()
        userFolderName = folderModel.GetUserFolderName()
        owner = folderModel.GetOwner()
        ownerUsername = folderModel.GetOwner().GetUsername()
        try:
            ownerUserId = folderModel.GetOwner().GetJson()['id']
        except:
            ownerUserId = None

        uploaderName = settingsModel.GetUploaderModel().GetName()
        uploaderUuid = settingsModel.GetUploaderModel().GetUuid()
        experimentTitle = folderModel.GetExperimentTitle()

        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = settingsModel.GetUsername()
        myTardisDefaultUserApiKey = settingsModel.GetApiKey()

        logger.debug("Creating experiment for uploader \"" +
                     uploaderName + ", user folder " + userFolderName)
        description = ("Uploader: %s\n\n"
                       "User folder name: %s"
                       % (uploaderName, userFolderName))
        experimentJson = {
            "title": experimentTitle,
            "description": description,
            "immutable": False,
            "parameter_sets": [{
                "schema": "http://mytardis.org/schemas"
                          "/mydata/defaultexperiment",
                "parameters": [{"name": "uploader",
                                "value": uploaderUuid},
                               {"name": "user_folder_name",
                                "value": userFolderName}]}]}
        headers = {"Authorization": "ApiKey " +
                   myTardisDefaultUsername + ":" +
                   myTardisDefaultUserApiKey,
                   "Content-Type": "application/json",
                   "Accept": "application/json"}
        url = myTardisUrl + "/api/v1/mydata_experiment/"
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
            logger.debug("Succeeded in creating experiment for uploader "
                         "\"%s\" and user folder \"%s\""
                         % (uploaderName, userFolderName))

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
            logger.debug("Failed to create experiment for uploader "
                         "\"%s\" and user folder \"%s\""
                         % (uploaderName, userFolderName))
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
                modelClassOfObjectNotFound = None
                try:
                    errorResponse = response.json()
                    if errorResponse['error_message'] == \
                            "UserProfile matching query does not exist.":
                        modelClassOfObjectNotFound = UserProfileModel
                    elif errorResponse['error_message'] == \
                            "Schema matching query does not exist.":
                        modelClassOfObjectNotFound = SchemaModel
                    elif errorResponse['error_message'] == \
                            "Sorry, this request could not be processed. " \
                            "Please try again later.":
                        raise Exception("TASTYPIE_CANNED_ERROR")
                    message += "A 404 (Not Found) error occurred while " \
                               "attempting to create an experiment " \
                               "record:\n\n" \
                               "    %s\n\n" % errorResponse['error_message']
                except:
                    message += "A 404 (Not Found) error occurred while " \
                               "attempting to create an experiment " \
                               "record.  This could be caused by a missing " \
                               "UserProfile record for user \"%s\" or it " \
                               "could be caused by a missing Schema record " \
                               "(see https://github.com/wettenhj/" \
                               "mytardis-app-mydata/blob/master/README.md)" \
                               "\n\n" \
                               "Turning on DEBUG mode on the MyTardis " \
                               "server could help to isolate the problem." \
                               % myTardisDefaultUsername
                if modelClassOfObjectNotFound == UserProfileModel:
                    message += "Please ask your MyTardis administrator to " \
                               "ensure that a User Profile record exists " \
                               "for the \"%s\" user account." \
                               % myTardisDefaultUsername
                elif modelClassOfObjectNotFound == SchemaModel:
                    message += "Please ask your MyTardis administrator to " \
                               "create the experiment metadata schema " \
                               "described in the \"MyTardis Prerequisites\" " \
                               "section of the MyData documentation:\n\n" \
                               "http://mydata.readthedocs.org/en/latest/" \
                               "mytardis-prerequisites.html"
                raise DoesNotExist(message,
                                   modelClass=modelClassOfObjectNotFound)
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

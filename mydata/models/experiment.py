"""
Model class for MyTardis API v1's ExperimentResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

# pylint: disable=missing-docstring

import json
import urllib2
import requests

from mydata.logs import logger
from mydata.utils.exceptions import Unauthorized
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import MultipleObjectsReturned
from .user import UserProfileModel
from .objectacl import ObjectAclModel
from .schema import SchemaModel


class ExperimentModel(object):
    """
    Model class for MyTardis API v1's ExperimentResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    def __init__(self, settingsModel, experimentJson):
        self.settingsModel = settingsModel
        self.json = experimentJson

    @staticmethod
    def GetOrCreateExperimentForFolder(folderModel, testRun=False):
        """
        See also GetExperimentForFolder, CreateExperimentForFolder
        """
        try:
            existingExperiment = \
                ExperimentModel.GetExperimentForFolder(folderModel)
            if testRun:
                message = "ADDING TO EXISTING EXPERIMENT FOR FOLDER: %s\n" \
                    "    URL: %s/%s\n" \
                    "    Title: %s\n" \
                    "    Owner: %s" \
                    % (folderModel.GetRelPath(),
                       folderModel.settingsModel.GetMyTardisUrl(),
                       existingExperiment.GetViewUri(),
                       existingExperiment.GetTitle(),
                       folderModel.GetOwner().GetUsername())
                logger.testrun(message)
            return existingExperiment
        except DoesNotExist, err:
            if err.GetModelClass() == ExperimentModel:
                return ExperimentModel.CreateExperimentForFolder(folderModel,
                                                                 testRun)
            else:
                raise

    @staticmethod
    def GetExperimentForFolder(folderModel):
        """
        See also GetOrCreateExperimentForFolder
        """
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        settingsModel = folderModel.GetSettingsModel()

        uploaderName = settingsModel.GetUploaderModel().GetName()
        uploaderUuid = settingsModel.GetUploaderModel().GetUuid()
        userFolderName = folderModel.GetUserFolderName()
        groupFolderName = folderModel.GetGroupFolderName()
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = settingsModel.GetUsername()
        myTardisDefaultUserApiKey = settingsModel.GetApiKey()
        experimentTitle = folderModel.GetExperimentTitle()

        if folderModel.ExperimentTitleSetManually():
            expTitleEncoded = urllib2.quote(experimentTitle.encode('utf-8'))
            folderStructureEncoded = \
                urllib2.quote(settingsModel.GetFolderStructure())
            url = myTardisUrl + "/api/v1/mydata_experiment/?format=json" + \
                "&title=" + expTitleEncoded + \
                "&folder_structure=" + folderStructureEncoded
        else:
            url = myTardisUrl + "/api/v1/mydata_experiment/?format=json" + \
                "&uploader=" + uploaderUuid
        if userFolderName:
            url += "&user_folder_name=" + \
                urllib2.quote(userFolderName.encode('utf-8'))
        if groupFolderName:
            url += "&group_folder_name=" + \
                urllib2.quote(groupFolderName.encode('utf-8'))

        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisDefaultUsername,
                                               myTardisDefaultUserApiKey)}
        response = requests.get(url=url, headers=headers)
        try:
            experimentsJson = response.json()
            numExperimentsFound = experimentsJson['meta']['total_count']
            logger.debug(url)
        except:
            logger.error(url)
            logger.error(response.text)
            logger.error("response.status_code = " + str(response.status_code))
            if response.status_code == 404:
                message = "Failed to confirm existence of experiment \"%s\" " \
                          "for folder \"%s\"." \
                          % (experimentTitle, folderModel.GetFolder())
                message += "\n\n"
                modelClassOfObjectNotFound = None
                # pylint: disable=bare-except
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
                               "(see https://github.com/mytardis/" \
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
                if userFolderName:
                    message = "Experiment not found for '%s', %s, '%s'" \
                        % (uploaderName, userFolderName, experimentTitle)
                    if groupFolderName:
                        message += ", '%s'" % groupFolderName
                elif groupFolderName:
                    message = "Experiment not found for '%s', %s, '%s'" \
                        % (uploaderName, groupFolderName, experimentTitle)
                else:
                    message = "Experiment not found for '%s', '%s'" \
                        % (uploaderName, experimentTitle)
            else:
                if userFolderName:
                    message = "Experiment not found for '%s', %s" \
                        % (uploaderName, userFolderName)
                    if groupFolderName:
                        message += ", '%s'" % groupFolderName
                elif groupFolderName:
                    message = "Experiment not found for '%s', %s" \
                        % (uploaderName, groupFolderName)
                else:
                    message = "Experiment not found for '%s'." % uploaderName

            logger.debug(message)
            raise DoesNotExist(message, modelClass=ExperimentModel)
        elif numExperimentsFound == 1 or \
                folderModel.ExperimentTitleSetManually():
            # When an experiment is created for a single MyData
            # uploader instance, we shouldn't find any duplicates,
            # but when MyData is instructed to add datasets to an
            # existing experiment (e.g. the "Experiment / Data"
            # folder structure), we don't raise a critical error
            # for duplicate experiments - instead we just use the
            # first one we find.
            if folderModel.ExperimentTitleSetManually():
                if userFolderName:
                    message = "Found existing experiment with title '%s' " \
                        "and user folder '%s'" % (experimentTitle,
                                                  userFolderName)
                    if groupFolderName:
                        message += " and group folder '%s'." % groupFolderName
                elif groupFolderName:
                    message = "Found existing experiment with title '%s' " \
                        "and user group folder '%s'" % (experimentTitle,
                                                        groupFolderName)
                else:
                    message = "Found existing experiment with title '%s'." \
                        % experimentTitle
            else:
                if userFolderName:
                    message = "Found existing experiment for uploader '%s' " \
                        "and user folder '%s'." % (uploaderName,
                                                   userFolderName)
                    if groupFolderName:
                        message += " and group folder '%s'." % groupFolderName
                elif groupFolderName:
                    message = "Found existing experiment for uploader '%s' " \
                        "and user group folder '%s'." % (uploaderName,
                                                         groupFolderName)
                else:
                    message = "Found existing experiment for uploader '%s'." \
                        % uploaderName

            logger.debug(message)
            return ExperimentModel(settingsModel,
                                   experimentsJson['objects'][0])
        elif numExperimentsFound > 1:
            message = "ERROR: Found multiple experiments matching " + \
                "Uploader UUID for user '%s'" % userFolderName
            if groupFolderName:
                message += " and group '%s'" % groupFolderName
            logger.error(message)
            for expJson in experimentsJson['objects']:
                logger.error("\t" + expJson['title'])
            groupFolderString = ""
            if groupFolderName:
                groupFolderString = ", and group folder \"%s\"" \
                    % groupFolderName
            message = "Multiple experiments were found matching " \
                      "uploader \"%s\" and user folder \"%s\"%s " \
                      "for folder \"%s\"." \
                      % (uploaderName, userFolderName, groupFolderString,
                         folderModel.GetFolder())
            message += "\n\n"
            message += "This shouldn't happen.  Please ask your " \
                       "MyTardis administrator to investigate."
            raise MultipleObjectsReturned(message)

    @staticmethod
    def CreateExperimentForFolder(folderModel, testRun=False):
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        settingsModel = folderModel.GetSettingsModel()
        userFolderName = folderModel.GetUserFolderName()
        hostname = settingsModel.GetUploaderModel().GetHostname()
        location = folderModel.GetLocation()
        groupFolderName = folderModel.GetGroupFolderName()
        owner = folderModel.GetOwner()
        ownerUsername = folderModel.GetOwner().GetUsername()
        # pylint: disable=bare-except
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

        if userFolderName:
            message = "Creating experiment for uploader '%s', " \
                "user folder '%s'." % (uploaderName, userFolderName)
            if groupFolderName:
                message += ", group folder : '%s'" % groupFolderName
        elif groupFolderName:
            message = "Creating experiment for uploader '%s', " \
                "user group folder '%s'." % (uploaderName, groupFolderName)
        else:
            message = "Creating experiment for uploader '%s'" % uploaderName
        logger.info(message)
        if userFolderName:
            description = ("Uploader: %s\n"
                           "User folder name: %s\n"
                           "Uploaded from: %s:%s"
                           % (uploaderName, userFolderName, hostname, location))
            if groupFolderName:
                description += "\nGroup folder name: %s" % groupFolderName
        else:
            description = ("Uploader: %s\n"
                           "Group folder name: %s\n"
                           "Uploaded from: %s:%s"
                           % (uploaderName, groupFolderName, hostname, location))

        if testRun:
            message = "CREATING NEW EXPERIMENT FOR FOLDER: %s\n" \
                "    Title: %s\n" \
                "    Description: \n" \
                "        Uploader: %s\n" \
                "        User folder name: %s\n" \
                "    Owner: %s" \
                % (folderModel.GetRelPath(),
                   experimentTitle, uploaderName, userFolderName,
                   ownerUsername)
            logger.testrun(message)
            return

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
        if groupFolderName:
            experimentJson["parameter_sets"][0]["parameters"].append(
                {"name": "group_folder_name", "value": groupFolderName})
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisDefaultUsername,
                                               myTardisDefaultUserApiKey),
            "Content-Type": "application/json",
            "Accept": "application/json"}
        url = myTardisUrl + "/api/v1/mydata_experiment/"

        response = requests.post(headers=headers, url=url,
                                 data=json.dumps(experimentJson))
        # pylint: disable=bare-except
        try:
            createdExperimentJson = response.json()
            createdExperiment = ExperimentModel(settingsModel,
                                                createdExperimentJson)
            logger.debug(url)
        except:
            logger.error(url)
            logger.error(response.text)
            logger.error("response.status_code = " +
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
            message = "Succeeded in creating experiment '%s' for uploader " \
                "\"%s\" and user folder \"%s\"" \
                % (experimentTitle, uploaderName, userFolderName)
            if groupFolderName:
                message += " and group folder \"%s\"" % groupFolderName
            logger.debug(message)

            facilityManagersGroup = settingsModel.GetFacility().GetManagerGroup()
            ObjectAclModel.ShareExperimentWithGroup(createdExperiment,
                                                    facilityManagersGroup)
            # Avoid creating a duplicate ObjectACL if the user folder's
            # username matches the facility manager's username.
            # Don't attempt to create an ObjectACL record for an
            # invalid user (without a MyTardis user ID).
            if myTardisDefaultUsername != ownerUsername and \
                    ownerUserId is not None:
                ObjectAclModel.ShareExperimentWithUser(createdExperiment,
                                                       owner)
            if folderModel.GetGroup() is not None and \
                    folderModel.GetGroup().GetId() != \
                    facilityManagersGroup.GetId():
                ObjectAclModel.ShareExperimentWithGroup(createdExperiment,
                                                        folderModel.GetGroup())
        else:
            message = "Failed to create experiment for uploader " \
                "\"%s\" and user folder \"%s\"" \
                % (uploaderName, userFolderName)
            if groupFolderName:
                message += " and group folder \"%s\"" % groupFolderName
            logger.error(message)
            logger.error(headers)
            logger.error(url)
            logger.error(response.text)
            logger.error("response.status_code = " +
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
                # pylint: disable=bare-except
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
                               "(see https://github.com/mytardis/" \
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

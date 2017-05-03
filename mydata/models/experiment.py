"""
Model class for MyTardis API v1's ExperimentResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""
import json
import urllib
import requests

from ..settings import SETTINGS
from ..logs import logger
from ..utils.exceptions import Unauthorized
from ..utils.exceptions import DoesNotExist
from ..utils.exceptions import MultipleObjectsReturned
from .user import UserProfileModel
from .objectacl import ObjectAclModel
from .schema import SchemaModel
from . import HandleHttpError


class ExperimentModel(object):
    """
    Model class for MyTardis API v1's ExperimentResource.
    """
    def __init__(self, experimentJson):
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
                       SETTINGS.general.myTardisUrl,
                       existingExperiment.viewUri,
                       existingExperiment.title,
                       folderModel.owner.username)
                logger.testrun(message)
            return existingExperiment
        except DoesNotExist as err:
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
        uploaderName = SETTINGS.uploaderModel.name
        uploaderUuid = SETTINGS.miscellaneous.uuid
        userFolderName = folderModel.userFolderName
        groupFolderName = folderModel.groupFolderName
        myTardisUrl = SETTINGS.general.myTardisUrl
        experimentTitle = folderModel.experimentTitle

        if folderModel.experimentTitleSetManually:
            expTitleEncoded = urllib.quote(experimentTitle.encode('utf-8'))
            folderStructureEncoded = \
                urllib.quote(SETTINGS.advanced.folderStructure)
            url = "%s/api/v1/mydata_experiment/?format=json" \
                "&title=%s&folder_structure=%s" \
                % (myTardisUrl, expTitleEncoded, folderStructureEncoded)
        else:
            url = "%s/api/v1/mydata_experiment/?format=json" \
                "&uploader=%s" % (myTardisUrl, uploaderUuid)
        if userFolderName:
            url += "&user_folder_name=%s" \
                % urllib.quote(userFolderName.encode('utf-8'))
        if groupFolderName:
            url += "&group_folder_name=%s" \
                % urllib.quote(groupFolderName.encode('utf-8'))

        logger.debug(url)
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
        if response.status_code == 200:
            experimentsJson = response.json()
            numExperimentsFound = experimentsJson['meta']['total_count']
        else:
            if response.status_code == 404:
                try:
                    message = response.json()['error_message']
                    modelClassOfObjectNotFound = None
                    if "UserProfile" in message:
                        modelClassOfObjectNotFound = UserProfileModel
                    elif "Schema" in message:
                        modelClassOfObjectNotFound = SchemaModel
                    raise DoesNotExist(
                        message, modelClass=modelClassOfObjectNotFound)
                except (KeyError, ValueError):
                    message = "Received 404 while looking up experiment(s)"
                    raise DoesNotExist(message, modelClass=None)
            HandleHttpError(response)
        if numExperimentsFound == 0:
            if folderModel.experimentTitleSetManually:
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
                folderModel.experimentTitleSetManually:
            # When an experiment is created for a single MyData
            # uploader instance, we shouldn't find any duplicates,
            # but when MyData is instructed to add datasets to an
            # existing experiment (e.g. the "Experiment / Data"
            # folder structure), we don't raise a critical error
            # for duplicate experiments - instead we just use the
            # first one we find.
            if folderModel.experimentTitleSetManually:
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
            return ExperimentModel(experimentsJson['objects'][0])
        elif numExperimentsFound > 1:
            message = "ERROR: Found multiple experiments matching " \
                "Uploader UUID for user '%s'" % userFolderName
            if groupFolderName:
                message += " and group '%s'" % groupFolderName
            logger.error(message)
            for expJson in experimentsJson['objects']:
                logger.error("\t%s" % expJson['title'])
            groupFolderString = ""
            if groupFolderName:
                groupFolderString = ", and group folder \"%s\"" \
                    % groupFolderName
            message = "Multiple experiments were found matching " \
                      "uploader \"%s\" and user folder \"%s\"%s " \
                      "for folder \"%s\"." \
                      % (uploaderName, userFolderName, groupFolderString,
                         folderModel.folderName)
            message += "\n\n"
            message += "This shouldn't happen.  Please ask your " \
                       "MyTardis administrator to investigate."
            raise MultipleObjectsReturned(message)

    @staticmethod
    def CreateExperimentForFolder(folderModel, testRun=False):
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        """
        Create a MyTardis experiment to create this folder's dataset within
        """
        userFolderName = folderModel.userFolderName
        hostname = SETTINGS.uploaderModel.hostname
        location = folderModel.location
        groupFolderName = folderModel.groupFolderName
        owner = folderModel.owner
        ownerUsername = folderModel.owner.username
        try:
            ownerUserId = folderModel.owner.userId
        except:
            ownerUserId = None

        uploaderName = SETTINGS.uploaderModel.name
        uploaderUuid = SETTINGS.miscellaneous.uuid
        experimentTitle = folderModel.experimentTitle

        myTardisUrl = SETTINGS.general.myTardisUrl
        myTardisDefaultUsername = SETTINGS.general.username

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
                           % (uploaderName, userFolderName, hostname,
                              location))
            if groupFolderName:
                description += "\nGroup folder name: %s" % groupFolderName
        else:
            description = ("Uploader: %s\n"
                           "Group folder name: %s\n"
                           "Uploaded from: %s:%s"
                           % (uploaderName, groupFolderName, hostname,
                              location))

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
        url = "%s/api/v1/mydata_experiment/" % myTardisUrl
        logger.debug(url)
        response = requests.post(headers=SETTINGS.defaultHeaders,
                                 url=url, data=json.dumps(experimentJson))
        if response.status_code == 201:
            createdExperimentJson = response.json()
            createdExperiment = ExperimentModel(createdExperimentJson)
            message = "Succeeded in creating experiment '%s' for uploader " \
                "\"%s\" and user folder \"%s\"" \
                % (experimentTitle, uploaderName, userFolderName)
            if groupFolderName:
                message += " and group folder \"%s\"" % groupFolderName
            logger.debug(message)

            facilityManagersGroup = SETTINGS.facility.managerGroup
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
            if folderModel.group is not None and \
                    folderModel.group.groupId() != \
                    facilityManagersGroup.groupId:
                ObjectAclModel.ShareExperimentWithGroup(createdExperiment,
                                                        folderModel.group)
            return createdExperiment
        else:
            message = "Failed to create experiment for uploader " \
                "\"%s\" and user folder \"%s\"" \
                % (uploaderName, userFolderName)
            if groupFolderName:
                message += " and group folder \"%s\"" % groupFolderName
            logger.error(message)
            logger.error(url)
            logger.error(response.text)
            logger.error("response.status_code = " +
                         str(response.status_code))
            if response.status_code == 401:
                message = "Couldn't create experiment \"%s\" " \
                          "for folder \"%s\"." \
                          % (experimentTitle, folderModel.folderName)
                message += "\n\n"
                message += "Please ask your MyTardis administrator to " \
                           "check the permissions of the \"%s\" user " \
                           "account." % myTardisDefaultUsername
                raise Unauthorized(message)
            elif response.status_code == 404:
                message = "Couldn't create experiment \"%s\" " \
                          "for folder \"%s\"." \
                          % (experimentTitle, folderModel.folderName)
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

    @property
    def experimentId(self):
        """
        Return the experiment ID
        """
        return self.json['id']

    @property
    def title(self):
        """
        Return the experiment title
        """
        return self.json['title']

    @property
    def resourceUri(self):
        """
        Return the experiment's MyTardis API resource URI
        e.g. /api/v1/experiment/123/
        """
        return self.json['resource_uri']

    @property
    def viewUri(self):
        """
        Return the experiment's view URI
        """
        return "experiment/view/%d/" % self.experimentId

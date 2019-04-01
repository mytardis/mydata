"""
Model class for MyTardis API v1's ExperimentResource.
"""
import json

import requests
from six.moves import urllib

from ..settings import SETTINGS
from ..threads.flags import FLAGS
from ..logs import logger
from ..utils.exceptions import DoesNotExist
from .objectacl import ObjectAclModel


class ExperimentModel(object):
    """
    Model class for MyTardis API v1's ExperimentResource.
    """
    def __init__(self, experimentJson):
        self.json = experimentJson

    @staticmethod
    def GetOrCreateExperimentForFolder(folderModel):
        """
        See also GetExperimentForFolder, CreateExperimentForFolder
        """
        try:
            existingExperiment = \
                ExperimentModel.GetExperimentForFolder(folderModel)
            if FLAGS.testRunRunning:
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
                return ExperimentModel.CreateExperimentForFolder(folderModel)
            raise

    @staticmethod
    def GetExperimentForFolder(folderModel):
        """
        See also GetOrCreateExperimentForFolder
        """
        expTitleEncoded = urllib.parse.quote(
            folderModel.experimentTitle.encode('utf-8'))
        folderStructureEncoded = \
            urllib.parse.quote(SETTINGS.advanced.folderStructure)
        url = "%s/api/v1/mydata_experiment/?format=json" \
            "&title=%s&folder_structure=%s" \
            % (SETTINGS.general.myTardisUrl, expTitleEncoded,
               folderStructureEncoded)
        if folderModel.userFolderName:
            url += "&user_folder_name=%s" \
                % urllib.parse.quote(folderModel.userFolderName.encode('utf-8'))
        if folderModel.groupFolderName:
            url += "&group_folder_name=%s" \
                % urllib.parse.quote(folderModel.groupFolderName.encode('utf-8'))

        logger.debug(url)
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
        response.raise_for_status()
        experimentsJson = response.json()
        numExperimentsFound = experimentsJson['meta']['total_count']
        if numExperimentsFound == 0:
            message = ExperimentModel.LogExperimentNotFound(folderModel)
            raise DoesNotExist(message, modelClass=ExperimentModel)
        if numExperimentsFound >= 1:
            ExperimentModel.LogExperimentFound(folderModel)
            return ExperimentModel(experimentsJson['objects'][0])

        # Should never reach this, but it keeps Pylint happy:
        return None

    @staticmethod
    def CreateExperimentForFolder(folderModel):
        """
        Create a MyTardis experiment to create this folder's dataset within
        """
        userFolderName = folderModel.userFolderName
        groupFolderName = folderModel.groupFolderName
        try:
            ownerUserId = folderModel.owner.userId
        except:
            ownerUserId = None

        instrumentName = SETTINGS.general.instrument.name
        experimentTitle = folderModel.experimentTitle

        ExperimentModel.LogExperimentCreation(folderModel)
        if userFolderName:
            description = ("Instrument: %s\n"
                           "User folder name: %s\n"
                           "Uploaded from: %s:%s"
                           % (instrumentName, userFolderName,
                              SETTINGS.uploaderModel.hostname,
                              folderModel.location))
            if groupFolderName:
                description += "\nGroup folder name: %s" % groupFolderName
        else:
            description = ("Instrument: %s\n"
                           "Group folder name: %s\n"
                           "Uploaded from: %s:%s"
                           % (instrumentName, groupFolderName,
                              SETTINGS.uploaderModel.hostname,
                              folderModel.location))

        if FLAGS.testRunRunning:
            message = "CREATING NEW EXPERIMENT FOR FOLDER: %s\n" \
                "    Title: %s\n" \
                "    Description: \n" \
                "        Instrument: %s\n" \
                "        User folder name: %s\n" \
                "    Owner: %s" \
                % (folderModel.GetRelPath(),
                   experimentTitle, instrumentName, userFolderName,
                   folderModel.owner.username)
            logger.testrun(message)
            return None

        experimentJson = {
            "title": experimentTitle,
            "description": description,
            "immutable": False,
            "parameter_sets": [{
                "schema": "http://mytardis.org/schemas"
                          "/mydata/defaultexperiment",
                "parameters": [{"name": "uploader",
                                "value": SETTINGS.miscellaneous.uuid},
                               {"name": "user_folder_name",
                                "value": userFolderName}]}]}
        if groupFolderName:
            experimentJson["parameter_sets"][0]["parameters"].append(
                {"name": "group_folder_name", "value": groupFolderName})
        url = "%s/api/v1/mydata_experiment/" % SETTINGS.general.myTardisUrl
        logger.debug(url)
        response = requests.post(headers=SETTINGS.defaultHeaders,
                                 url=url, data=json.dumps(experimentJson).encode())
        response.raise_for_status()
        createdExperimentJson = response.json()
        createdExperiment = ExperimentModel(createdExperimentJson)
        message = "Succeeded in creating experiment '%s' for uploader " \
            "\"%s\" and user folder \"%s\"" \
            % (experimentTitle, instrumentName, userFolderName)
        if groupFolderName:
            message += " and group folder \"%s\"" % groupFolderName
        logger.debug(message)

        facilityManagersGroup = SETTINGS.general.facility.managerGroup
        ObjectAclModel.ShareExperimentWithGroup(
            createdExperiment, facilityManagersGroup, isOwner=False)
        # Avoid creating a duplicate ObjectACL if the user folder's
        # username matches the facility manager's username.
        # Don't attempt to create an ObjectACL record for an
        # invalid user (without a MyTardis user ID).
        if SETTINGS.general.username != folderModel.owner.username and \
                ownerUserId is not None:
            ObjectAclModel.ShareExperimentWithUser(createdExperiment,
                                                   folderModel.owner)
        if folderModel.group is not None and \
                folderModel.group.groupId != \
                facilityManagersGroup.groupId:
            ObjectAclModel.ShareExperimentWithGroup(
                createdExperiment, folderModel.group, isOwner=True)
        return createdExperiment

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

    @staticmethod
    def LogExperimentCreation(folderModel):
        """
        Log a message about the experiment's creation
        """
        instrumentName = SETTINGS.general.instrument.name

        if folderModel.userFolderName:
            message = "Creating experiment for instrument '%s', " \
                "user folder '%s'." % (
                    instrumentName, folderModel.userFolderName)
            if folderModel.groupFolderName:
                message += ", group folder : '%s'" \
                    % folderModel.groupFolderName
        elif folderModel.groupFolderName:
            message = "Creating experiment for uploader '%s', " \
                "user group folder '%s'." % (
                    instrumentName, folderModel.groupFolderName)
        else:
            message = \
                "Creating experiment for uploader '%s'" % instrumentName
        logger.info(message)
        return message

    @staticmethod
    def LogExperimentNotFound(folderModel):
        """
        Log a message about an experiment not being found.  This doesn't
        deserve a warning-level log message, because it's quite normal for
        MyData to find that it needs to create an experiment rather than
        using an existing one.
        """
        if folderModel.userFolderName:
            message = "Experiment not found for %s, '%s'" \
                % (folderModel.userFolderName, folderModel.experimentTitle)
            if folderModel.groupFolderName:
                message += ", '%s'" % folderModel.groupFolderName
        elif folderModel.groupFolderName:
            message = "Experiment not found for %s, '%s'" \
                % (folderModel.groupFolderName, folderModel.experimentTitle)
        else:
            message = \
                "Experiment not found for '%s'" % folderModel.experimentTitle
        logger.debug(message)
        return message

    @staticmethod
    def LogExperimentFound(folderModel):
        """
        Log a message about an existing experiment being found
        """
        if folderModel.userFolderName:
            message = "Found existing experiment with title '%s' " \
                "and user folder '%s'" % (folderModel.experimentTitle,
                                          folderModel.userFolderName)
            if folderModel.groupFolderName:
                message += " and group folder '%s'." \
                    % folderModel.groupFolderName
        elif folderModel.groupFolderName:
            message = "Found existing experiment with title '%s' " \
                "and user group folder '%s'" % (folderModel.experimentTitle,
                                                folderModel.groupFolderName)
        else:
            message = "Found existing experiment with title '%s'." \
                % folderModel.experimentTitle
        logger.debug(message)
        return message

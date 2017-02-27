"""
Model class for MyTardis API v1's ObjectACLResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import json
import requests

from ..logs import logger
from ..utils.exceptions import Unauthorized
from ..utils.exceptions import DoesNotExist
from .user import UserProfileModel


class ObjectAclModel(object):
    """
    Model class for MyTardis API v1's ObjectACLResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    @staticmethod
    def ShareExperimentWithUser(experiment, user):
        """
        Grants full ownership of experiment to user.
        """
        logger.debug("\nSharing via ObjectACL with username \"" +
                     user.GetUsername() + "\"...\n")

        settings = experiment.settingsModel
        myTardisUrl = settings.general.myTardisUrl
        myTardisDefaultUsername = settings.general.username

        objectAclJson = {
            "pluginId": "django_user",
            "entityId": str(user.userId),
            "content_object": experiment.GetResourceUri().replace("mydata_",
                                                                  ""),
            "content_type": "experiment",
            "object_id": experiment.GetId(),
            "aclOwnershipType": 1,
            "isOwner": True,
            "canRead": True,
            "canWrite": True,
            "canDelete": False,
            "effectiveDate": None,
            "expiryDate": None}

        url = myTardisUrl + "/api/v1/objectacl/"
        response = requests.post(headers=settings.defaultHeaders, url=url,
                                 data=json.dumps(objectAclJson))
        if response.status_code == 201:
            logger.debug("Shared experiment with user " +
                         user.GetUsername() + ".")
        else:
            logger.debug(url)
            logger.debug(response.text)
            logger.debug("response.status_code = " +
                         str(response.status_code))
            if response.status_code == 401:
                message = "Couldn't create ObjectACL for " \
                          "experiment \"%s\"." % experiment.GetTitle()
                message += "\n\n"
                message += "Please ask your MyTardis administrator " \
                           "to check the permissions of the \"%s\" " \
                           "user account." % myTardisDefaultUsername
                raise Unauthorized(message)
            elif response.status_code == 404:
                message = "Couldn't create ObjectACL for " \
                          "experiment \"%s\"." % experiment.GetTitle()
                message += "\n\n"
                message += "A 404 (Not Found) error occurred while " \
                           "attempting to create the ObjectACL.\n\n" \
                           "Please ask your MyTardis administrator " \
                           "to check that a User Profile record " \
                           "exists for the \"%s\" user account." \
                           % myTardisDefaultUsername
                raise DoesNotExist(message, modelClass=UserProfileModel)

    @staticmethod
    def ShareExperimentWithGroup(experiment, group):
        """
        Grants read access to experiment to group.
        """
        logger.debug("\nSharing via ObjectACL with group \"" +
                     group.name + "\"...\n")

        settings = experiment.settingsModel
        myTardisUrl = settings.general.myTardisUrl
        myTardisDefaultUsername = settings.general.username

        objectAclJson = {
            "pluginId": "django_group",
            "entityId": str(group.groupId),
            "content_object": experiment.GetResourceUri().replace("mydata_",
                                                                  ""),
            "content_type": "experiment",
            "object_id": experiment.GetId(),
            "aclOwnershipType": 1,
            "isOwner": True,
            "canRead": True,
            "canWrite": True,
            "canDelete": False,
            "effectiveDate": None,
            "expiryDate": None}

        url = myTardisUrl + "/api/v1/objectacl/"
        response = requests.post(headers=settings.defaultHeaders, url=url,
                                 data=json.dumps(objectAclJson))
        if response.status_code == 201:
            logger.debug("Shared experiment with group " +
                         group.name + ".")
        else:
            logger.debug(url)
            logger.debug(response.text)
            logger.debug("response.status_code = " +
                         str(response.status_code))
            if response.status_code == 401:
                message = "Couldn't create ObjectACL for " \
                          "experiment \"%s\"." % experiment.GetTitle()
                message += "\n\n"
                message += "Please ask your MyTardis administrator " \
                           "to check the permissions of the \"%s\" " \
                           "user account." % myTardisDefaultUsername
                raise Unauthorized(message)
            elif response.status_code == 404:
                message = "Couldn't create ObjectACL for " \
                          "experiment \"%s\"." % experiment.GetTitle()
                message += "\n\n"
                message += "A 404 (Not Found) error occurred while " \
                           "attempting to create the ObjectACL.\n\n" \
                           "Please ask your MyTardis administrator " \
                           "to check that a User Profile record " \
                           "exists for the \"%s\" user account." \
                           % myTardisDefaultUsername
                raise DoesNotExist(message, modelClass=UserProfileModel)

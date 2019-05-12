"""
Model class for MyTardis API v1's ObjectACLResource.
"""

import json
import requests

from ..settings import SETTINGS
from ..logs import logger


class ObjectAclModel(object):
    """
    Model class for MyTardis API v1's ObjectACLResource.
    """
    @staticmethod
    def ShareExperimentWithUser(experiment, user):
        """
        Grants full ownership of experiment to user.
        """
        logger.debug("\nSharing via ObjectACL with username \"" +
                     user.username + "\"...\n")

        myTardisUrl = SETTINGS.general.myTardisUrl

        objectAclJson = {
            "pluginId": "django_user",
            "entityId": str(user.userId),
            "content_object": experiment.resourceUri.replace("mydata_", ""),
            "content_type": "experiment",
            "object_id": experiment.experimentId,
            "aclOwnershipType": 1,
            "isOwner": True,
            "canRead": True,
            "canWrite": True,
            "canDelete": False,
            "effectiveDate": None,
            "expiryDate": None}

        url = myTardisUrl + "/api/v1/objectacl/"
        response = requests.post(headers=SETTINGS.defaultHeaders, url=url,
                                 data=json.dumps(objectAclJson).encode())
        response.raise_for_status()
        logger.debug("Shared experiment with user " + user.username + ".")

    @staticmethod
    def ShareExperimentWithGroup(experiment, group, isOwner):
        """
        Grants read access to experiment to group.
        """
        logger.debug("\nSharing via ObjectACL with group \"" +
                     group.name + "\"...\n")

        myTardisUrl = SETTINGS.general.myTardisUrl

        objectAclJson = {
            "pluginId": "django_group",
            "entityId": str(group.groupId),
            "content_object": experiment.resourceUri.replace("mydata_", ""),
            "content_type": "experiment",
            "object_id": experiment.experimentId,
            "aclOwnershipType": 1,
            "isOwner": isOwner,
            "canRead": True,
            "canWrite": True,
            "canDelete": False,
            "effectiveDate": None,
            "expiryDate": None}

        url = myTardisUrl + "/api/v1/objectacl/"
        response = requests.post(headers=SETTINGS.defaultHeaders, url=url,
                                 data=json.dumps(objectAclJson).encode())
        response.raise_for_status()
        logger.debug("Shared experiment with group " + group.name + ".")

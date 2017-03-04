"""
Model class for MyTardis API v1's GroupResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""
import urllib
import requests

from ..settings import SETTINGS
from ..logs import logger
from ..utils.exceptions import DoesNotExist
from . import HandleHttpError


class GroupModel(object):
    """
    Model class for MyTardis API v1's GroupResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    def __init__(self, name=None, groupJson=None):
        self.groupId = None
        self.name = name
        self.groupJson = groupJson
        self.dataViewId = 0

        if groupJson is not None:
            self.groupId = groupJson['id']
            if name is None:
                self.name = groupJson['name']

        self.shortName = name
        length = len(SETTINGS.advanced.groupPrefix)
        self.shortName = self.name[length:]

    def GetValueForKey(self, key):
        """
        Return value of field from the Group model
        to display in the Groups or Folders view
        """
        return self.__dict__[key]

    @staticmethod
    def GetGroupByName(name):
        """
        Return the group record matching the supplied name
        """
        url = "%s/api/v1/group/?format=json&name=%s" \
            % (SETTINGS.general.myTardisUrl,
               urllib.quote(name.encode('utf-8')))
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
        if response.status_code != 200:
            HandleHttpError(response)
        groupsJson = response.json()
        numGroupsFound = groupsJson['meta']['total_count']

        if numGroupsFound == 0:
            raise DoesNotExist(
                message="Group \"%s\" was not found in MyTardis" % name,
                response=response)
        else:
            logger.debug("Found group record for name '" + name + "'.")
            return GroupModel(name=name, groupJson=groupsJson['objects'][0])

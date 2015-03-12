import requests
import json
import urllib

from logger.Logger import logger
from Exceptions import DoesNotExist


class GroupModel():

    def __init__(self, settingsModel=None, name=None, groupJson=None):
        self.settingsModel = settingsModel
        self.id = None
        self.name = name
        self.groupJson = groupJson

        if groupJson is not None:
            self.id = groupJson['id']
            if name is None:
                self.name = groupJson['name']

        self.shortName = name
        if settingsModel is not None:
            l = len(settingsModel.GetGroupPrefix())
            self.shortName = self.name[l:]

    def __str__(self):
        return "GroupModel " + self.name

    def __unicode__(self):
        return "GroupModel " + self.name

    def __repr__(self):
        return "GroupModel " + self.name

    def GetId(self):
        return self.id

    def GetDataViewId(self):
        return self.dataViewId

    def SetDataViewId(self, dataViewId):
        self.dataViewId = dataViewId

    def GetName(self):
        return self.name

    def GetShortName(self):
        return self.shortName

    def GetJson(self):
        return self.groupJson

    def GetValueForKey(self, key):
        return self.__dict__[key]

    @staticmethod
    def GetGroupByName(settingsModel, name):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/group/?format=json&name=" + \
            urllib.quote(name)
        headers = {'Authorization': 'ApiKey ' + myTardisUsername + ":" +
                   myTardisApiKey}
        response = requests.get(url=url, headers=headers)
        if response.status_code != 200:
            logger.debug("Failed to look up group record for name \"" +
                         name + "\".")
            logger.debug(response.text)
            raise Exception(response.text)
        groupsJson = response.json()
        numGroupsFound = groupsJson['meta']['total_count']

        if numGroupsFound == 0:
            raise DoesNotExist(
                message="Group \"%s\" was not found in MyTardis" % name,
                url=url, response=response)
        else:
            logger.debug("Found group record for name '" + name + "'.")
            return GroupModel(settingsModel=settingsModel, name=name,
                              groupJson=groupsJson['objects'][0])

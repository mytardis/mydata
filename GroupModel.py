import requests
import json
import urllib

from logger.Logger import logger


class GroupModel():

    def __init__(self, settingsModel=None, name=None,
                 groupRecordJson=None):

        self.settingsModel = settingsModel
        self.id = None
        self.name = name
        self.groupRecordJson = groupRecordJson

        if groupRecordJson is not None:
            self.id = groupRecordJson['id']
            if name is None:
                self.name = groupRecordJson['name']

    def __str__(self):
        return "GroupModel " + self.name

    def __unicode__(self):
        return "GroupModel " + self.name

    def __repr__(self):
        return "GroupModel " + self.name

    def GetId(self):
        return self.id

    def GetName(self):
        return self.name

    def GetJson(self):
        return self.groupRecordJson

    @staticmethod
    def GetGroupRecord(settingsModel, name):
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
            return None
        groupRecordsJson = response.json()
        numGroupRecordsFound = groupRecordsJson['meta']['total_count']

        if numGroupRecordsFound == 0:
            logger.warning("Group \"%s\" was not found in MyTardis" % name)
        else:
            logger.debug("Found group record for name '" + name + "'.")
            return GroupModel(settingsModel=settingsModel, name=name,
                              groupRecordJson=groupRecordsJson['objects'][0])

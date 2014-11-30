import requests
import json

from logger.Logger import logger
from GroupModel import GroupModel


class UserModel():

    def __init__(self, settingsModel=None, dataViewId=None,
                 username=None, name=None,
                 email=None, userRecordJson=None):

        self.settingsModel = settingsModel
        self.id = None
        self.dataViewId = dataViewId
        self.username = username
        self.name = name
        self.email = email
        self.groups = []
        self.userRecordJson = userRecordJson

        if userRecordJson is not None:
            self.id = userRecordJson['id']
            if username is None:
                self.username = userRecordJson['username']
            if name is None:
                self.name = userRecordJson['first_name'] + " " + \
                    userRecordJson['last_name']
            if email is None:
                self.email = userRecordJson['email']
            for group in userRecordJson['groups']:
                self.groups.append(GroupModel(settingsModel=settingsModel,
                                              groupJson=group))

    def GetId(self):
        return self.id

    def GetDataViewId(self):
        return self.dataViewId

    def SetDataViewId(self, dataViewId):
        self.dataViewId = dataViewId

    def GetUsername(self):
        return self.username

    def GetName(self):
        return self.name

    def GetEmail(self):
        return self.email

    def GetGroups(self):
        return self.groups

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetJson(self):
        return self.userRecordJson

    def __str__(self):
        return "UserModel: " + self.GetUsername()

    def __unicode__(self):
        return "UserModel: " + self.GetUsername()

    def __repr__(self):
        return "UserModel: " + self.GetUsername()

    @staticmethod
    def GetUserRecord(settingsModel, username):

        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/user/?format=json&username=" + username
        headers = {'Authorization': 'ApiKey ' + myTardisUsername + ":" +
                   myTardisApiKey}
        response = requests.get(url=url, headers=headers)
        if response.status_code != 200:
            logger.debug("Failed to look up user record for username \"" +
                         username + "\".")
            logger.debug(response.text)
            return None
        userRecordsJson = response.json()
        numUserRecordsFound = userRecordsJson['meta']['total_count']

        if numUserRecordsFound == 0:
            logger.warning("User %s was not found in MyTardis" % username)
        else:
            logger.debug("Found user record for username '" + username + "'.")
            return UserModel(settingsModel=settingsModel, username=username,
                             userRecordJson=userRecordsJson['objects'][0])

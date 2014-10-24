import requests
import json
import threading

from ApiKeyModel import ApiKeyModel
from logger.Logger import logger


class UserModel():

    def __init__(self, settingsModel=None, id=None, username=None, name=None,
                 email=None, userRecordJson=None):

        self.settingsModel = settingsModel
        self.id = id
        self.username = username
        self.name = name
        self.email = email
        self.userRecordJson = userRecordJson

        if userRecordJson is not None:
            if username is None:
                self.username = userRecordJson['username']
            if name is None:
                self.name = userRecordJson['first_name'] + " " + \
                    userRecordJson['last_name']
            if email is None:
                self.email = userRecordJson['email']

    def GetId(self):
        return self.id

    def SetId(self, id):

        if threading.current_thread().name != "MainThread":
            raise Exception("UsersModel.SetId: Attempt to update data view model outside of MainThread!")

        self.id = id

    def GetUsername(self):
        return self.username

    def GetName(self):
        return self.name

    def GetEmail(self):
        return self.email

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetJson(self):
        return self.userRecordJson

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
            logger.warn("User %s was not found in MyTardis" % username)
        else:
            logger.debug("Found user record for username '" + username + "'.")
            return UserModel(settingsModel=settingsModel, username=username,
                             userRecordJson=userRecordsJson['objects'][0])

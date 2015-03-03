import requests
import json
import traceback

from logger.Logger import logger
from GroupModel import GroupModel
from Exceptions import IncompatibleMyTardisVersion
from Exceptions import DoesNotExist


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
            try:
                for group in userRecordJson['groups']:
                    self.groups.append(GroupModel(settingsModel=settingsModel,
                                                  groupJson=group))
            except KeyError:
                # 'groups' should be available in the user record's JSON
                # if using https://github.com/wettenhj/mytardis/tree/mydata
                message = "Incompatible MyTardis version" \
                    "\n\n" \
                    "You appear to be connecting to a MyTardis server whose " \
                    "MyTardis version doesn't provide some of the " \
                    "functionality required by MyData." \
                    "\n\n" \
                    "Please check that you are using the correct MyTardis " \
                    "URL and ask your MyTardis administrator to check " \
                    "that an appropriate version of MyTardis is installed."
                logger.error(traceback.format_exc())
                logger.error(message)
                raise IncompatibleMyTardisVersion(message)

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
    def GetUserByUsername(settingsModel, username):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/user/?format=json&username=" + username
        headers = {'Authorization': 'ApiKey ' + myTardisUsername + ":" +
                   myTardisApiKey}
        try:
            session = requests.Session()
            response = session.get(url=url, headers=headers)
        except:
            response.close()
            session.close()
            raise Exception(traceback.format_exc())
        if response.status_code != 200:
            message = response.text
            response.close()
            session.close()
            raise Exception(message)
        try:
            userRecordsJson = response.json()
        except:
            logger.error(traceback.format_exc())
            response.close()
            session.close()
            raise
        response.close()
        session.close()
        numUserRecordsFound = userRecordsJson['meta']['total_count']

        if numUserRecordsFound == 0:
            raise DoesNotExist(
                message="User \"%s\" was not found in MyTardis" % username,
                url=url, response=response)
        else:
            logger.debug("Found user record for username '" + username + "'.")
            return UserModel(settingsModel=settingsModel, username=username,
                             userRecordJson=userRecordsJson['objects'][0])

    @staticmethod
    def GetUserByEmail(settingsModel, email):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/user/?format=json&email=" + email
        headers = {'Authorization': 'ApiKey ' + myTardisUsername + ":" +
                   myTardisApiKey}
        try:
            session = requests.Session()
            response = session.get(url=url, headers=headers)
        except:
            response.close()
            session.close()
            raise Exception(traceback.format_exc())
        if response.status_code != 200:
            message = response.text
            response.close()
            session.close()
            raise Exception(message)
        try:
            userRecordsJson = response.json()
        except:
            logger.error(traceback.format_exc())
            response.close()
            session.close()
            raise
        response.close()
        session.close()
        numUserRecordsFound = userRecordsJson['meta']['total_count']

        if numUserRecordsFound == 0:
            raise DoesNotExist(
                message="User with email \"%s\" was not found in MyTardis"
                % email,
                url=url, response=response)
        else:
            logger.debug("Found user record for email '" + email + "'.")
            return UserModel(settingsModel=settingsModel,
                             userRecordJson=userRecordsJson['objects'][0])


class UserProfileModel():
    """
    Used with the DoesNotExist exception when a 404 from MyTardis's API
    is assumed to have been caused by a missing user profile record.
    """
    pass

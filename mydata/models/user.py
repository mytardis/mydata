"""
Model class for MyTardis API v1's UserResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""
import traceback
import urllib2
import requests

from mydata.utils.exceptions import IncompatibleMyTardisVersion
from mydata.utils.exceptions import DoesNotExist
from mydata.logs import logger
from .group import GroupModel


class UserModel(object):
    """
    Model class for MyTardis API v1's UserResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    # pylint: disable=missing-docstring
    # pylint: disable=too-many-instance-attributes
    userNotFoundString = "USER NOT FOUND IN MYTARDIS"

    def __init__(self, settingsModel=None, dataViewId=None,
                 username=None, name=None,
                 email=None, userRecordJson=None,
                 userNotFoundInMyTardis=False):
        # pylint: disable=too-many-arguments
        self.settingsModel = settingsModel
        self.userId = None
        self.dataViewId = dataViewId
        self.username = username
        self.name = name
        self.email = email
        self.groups = []
        self.userRecordJson = userRecordJson
        self.userNotFoundInMyTardis = userNotFoundInMyTardis

        if userRecordJson is not None:
            self.userId = userRecordJson['id']
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
        return self.userId

    def GetDataViewId(self):
        return self.dataViewId

    def SetDataViewId(self, dataViewId):
        self.dataViewId = dataViewId

    def GetUsername(self):
        if self.username:
            return self.username
        else:
            return UserModel.userNotFoundString

    def GetName(self):
        if self.name:
            return self.name
        else:
            return UserModel.userNotFoundString

    def GetEmail(self):
        if self.email:
            return self.email
        else:
            return UserModel.userNotFoundString

    def GetGroups(self):
        return self.groups

    def GetValueForKey(self, key):
        if self.__dict__[key]:
            return self.__dict__[key]
        if key in ('username', 'name', 'email') and \
                self.UserNotFoundInMyTardis():
            return UserModel.userNotFoundString
        else:
            return None

    def GetJson(self):
        return self.userRecordJson

    def UserNotFoundInMyTardis(self):
        return self.userNotFoundInMyTardis

    def __str__(self):
        return "UserModel: " + self.GetUsername()

    def __repr__(self):
        return "UserModel: " + self.GetUsername()

    @staticmethod
    def GetUserByUsername(settingsModel, username):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/user/?format=json&username=" + username
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey)}
        try:
            response = requests.get(url=url, headers=headers)
        except:
            raise Exception(traceback.format_exc())
        if response.status_code != 200:
            message = response.text
            raise Exception(message)
        try:
            userRecordsJson = response.json()
        except:
            logger.error(traceback.format_exc())
            raise
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

        url = myTardisUrl + "/api/v1/user/?format=json&email__iexact=" + \
            urllib2.quote(email)
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey)}
        try:
            response = requests.get(url=url, headers=headers)
        except:
            raise Exception(traceback.format_exc())
        if response.status_code != 200:
            logger.debug(url)
            message = response.text
            raise Exception(message)
        try:
            userRecordsJson = response.json()
        except:
            logger.error(traceback.format_exc())
            raise
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


# pylint: disable=too-few-public-methods
class UserProfileModel(object):
    """
    Used with the DoesNotExist exception when a 404 from MyTardis's API
    is assumed to have been caused by a missing user profile record.
    """
    pass

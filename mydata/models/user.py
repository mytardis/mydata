"""
Model class for MyTardis API v1's UserResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""
import urllib
import requests

from ..utils.exceptions import DoesNotExist
from ..logs import logger
from .group import GroupModel
from . import HandleHttpError


class UserModel(object):
    """
    Model class for MyTardis API v1's UserResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    userNotFoundString = "USER NOT FOUND IN MYTARDIS"

    def __init__(self, settingsModel=None, dataViewId=None,
                 username=None, name=None,
                 email=None, userRecordJson=None,
                 userNotFoundInMyTardis=False):
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
            for group in userRecordJson['groups']:
                self.groups.append(GroupModel(settingsModel=settingsModel,
                                              groupJson=group))

    def GetUsername(self):
        """
        Return the username or a string indicating that
        the user was not found on the MyTardis server
        """
        if self.username:
            return self.username
        else:
            return UserModel.userNotFoundString

    def GetName(self):
        """
        Return the user's full name or a string indicating
        that the user was not found on the MyTardis server
        """
        if self.name:
            return self.name
        else:
            return UserModel.userNotFoundString

    def GetEmail(self):
        """
        Return the user's email address or a string indicating
        that the user was not found on the MyTardis server
        """
        if self.email:
            return self.email
        else:
            return UserModel.userNotFoundString

    def GetValueForKey(self, key):
        """
        Return value of field from the User model
        to display in the Users or Folders view
        """
        if key in self.__dict__ and self.__dict__[key]:
            return self.__dict__[key]
        elif key in ('username', 'name', 'email') and \
                self.userNotFoundInMyTardis:
            return UserModel.userNotFoundString
        else:
            return None

    @staticmethod
    def GetUserByUsername(settings, username):
        """
        Get user by username
        """
        url = "%s/api/v1/user/?format=json&username=%s" \
            % (settings.general.myTardisUrl, username)
        response = requests.get(url=url, headers=settings.defaultHeaders)
        if response.status_code != 200:
            HandleHttpError(response)
        userRecordsJson = response.json()
        numUserRecordsFound = userRecordsJson['meta']['total_count']

        if numUserRecordsFound == 0:
            raise DoesNotExist(
                message="User \"%s\" was not found in MyTardis" % username,
                response=response)
        else:
            logger.debug("Found user record for username '" + username + "'.")
            return UserModel(settingsModel=settings, username=username,
                             userRecordJson=userRecordsJson['objects'][0])

    @staticmethod
    def GetUserByEmail(settings, email):
        """
        Get user by email
        """
        url = "%s/api/v1/user/?format=json&email__iexact=%s" \
            % (settings.general.myTardisUrl,
               urllib.quote(email.encode('utf-8')))
        response = requests.get(url=url, headers=settings.defaultHeaders)
        if response.status_code != 200:
            HandleHttpError(response)
        userRecordsJson = response.json()
        numUserRecordsFound = userRecordsJson['meta']['total_count']

        if numUserRecordsFound == 0:
            raise DoesNotExist(
                message="User with email \"%s\" was not found in MyTardis"
                % email,
                response=response)
        else:
            logger.debug("Found user record for email '" + email + "'.")
            return UserModel(settingsModel=settings,
                             userRecordJson=userRecordsJson['objects'][0])


class UserProfileModel(object):
    """
    Used with the DoesNotExist exception when a 404 from MyTardis's API
    is assumed to have been caused by a missing user profile record.
    """
    pass

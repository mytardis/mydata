"""
Model class for MyTardis API v1's UserResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""
import urllib
import requests

from ..settings import SETTINGS
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

    def __init__(self, dataViewId=None, username=None, fullName=None, email=None,
                 userRecordJson=None, userNotFoundInMyTardis=False):
        self.userId = None
        self.dataViewId = dataViewId
        self._username = username
        self._fullName = fullName
        self._email = email
        self.groups = []
        self.userNotFoundInMyTardis = userNotFoundInMyTardis

        if userRecordJson is not None:
            self.userId = userRecordJson['id']
            if username is None:
                self._username = userRecordJson['username']
            if fullName is None:
                self._fullName = userRecordJson['first_name'] + " " + \
                    userRecordJson['last_name']
            if email is None:
                self._email = userRecordJson['email']
            for group in userRecordJson['groups']:
                self.groups.append(GroupModel(groupJson=group))

    @property
    def username(self):
        """
        Return the username or a string indicating that
        the user was not found on the MyTardis server
        """
        if self._username:
            return self._username
        else:
            return UserModel.userNotFoundString

    @username.setter
    def username(self, username):
        """
        Set the username
        """
        self._username = username

    @property
    def fullName(self):
        """
        Return the user's full name or a string indicating
        that the user was not found on the MyTardis server
        """
        if self._fullName:
            return self._fullName
        else:
            return UserModel.userNotFoundString

    @fullName.setter
    def fullName(self, fullName):
        """
        Set the user's full name
        """
        self._fullName = fullName

    @property
    def email(self):
        """
        Return the user's email address or a string indicating
        that the user was not found on the MyTardis server
        """
        if self._email:
            return self._email
        else:
            return UserModel.userNotFoundString

    @email.setter
    def email(self, email):
        """
        Set the user's email address
        """
        self._email = email

    def GetValueForKey(self, key):
        """
        Return value of field from the User model
        to display in the Users or Folders view
        """
        if hasattr(self, key) and getattr(self, key, None):
            return getattr(self, key)
        elif key in ('username', 'fullName', 'email') and \
                self.userNotFoundInMyTardis:
            return UserModel.userNotFoundString
        else:
            return None

    @staticmethod
    def GetUserByUsername(username):
        """
        Get user by username
        """
        url = "%s/api/v1/user/?format=json&username=%s" \
            % (SETTINGS.general.myTardisUrl, username)
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
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
            return UserModel(username=username,
                             userRecordJson=userRecordsJson['objects'][0])

    @staticmethod
    def GetUserByEmail(email):
        """
        Get user by email
        """
        url = "%s/api/v1/user/?format=json&email__iexact=%s" \
            % (SETTINGS.general.myTardisUrl,
               urllib.quote(email.encode('utf-8')))
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
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
            return UserModel(userRecordJson=userRecordsJson['objects'][0])


class UserProfileModel(object):
    """
    Used with the DoesNotExist exception when a 404 from MyTardis's API
    is assumed to have been caused by a missing user profile record.
    """
    pass

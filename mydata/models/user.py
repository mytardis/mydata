"""
Model class for MyTardis API v1's UserResource.
"""
import urllib

import requests

from ..settings import SETTINGS
from ..utils.exceptions import DoesNotExist
from ..logs import logger
from .group import GroupModel


class UserModel(object):
    """
    Model class for MyTardis API v1's UserResource.
    """
    userNotFoundString = "USER NOT FOUND IN MYTARDIS"

    def __init__(self, dataViewId=None, username=None,
                 fullName=None, email=None,
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
            username = self._username
        else:
            username = UserModel.userNotFoundString
        return username

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
            fullName = self._fullName
        else:
            fullName = UserModel.userNotFoundString
        return fullName

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
            email = self._email
        else:
            email = UserModel.userNotFoundString
        return email

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
        if key in ('username', 'fullName', 'email') and \
                self.userNotFoundInMyTardis:
            value = UserModel.userNotFoundString
        else:
            value = None
        return value

    @staticmethod
    def GetUserByUsername(username):
        """
        Get user by username

        :raises requests.exceptions.HTTPError:
        """
        url = "%s/api/v1/user/?format=json&username=%s" \
            % (SETTINGS.general.myTardisUrl, username)
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
        response.raise_for_status()
        userRecordsJson = response.json()

        if userRecordsJson["meta"]["total_count"] == 0:
            """
            Let's check if user has been migrated from LDAP to AAF
            """
            url = "%s/api/v1/mydata_user/?username=%s" \
                  % (SETTINGS.general.myTardisUrl, username)
            try:
                rsp = requests.get(url=url, headers=SETTINGS.defaultHeaders)
                data = rsp.json()
                userFound = data["success"]
            except:
                userFound = False
            if userFound:
                return UserModel.GetUserByUsername(data["username"])
            else:
                raise DoesNotExist(
                    message="User \"%s\" was not found in MyTardis" % username,
                    response=response)
        logger.debug("Found user record for username '" + username + "'.")
        return UserModel(username=username,
                         userRecordJson=userRecordsJson["objects"][0])

    @staticmethod
    def GetUserByEmail(email):
        """
        Get user by email

        :raises requests.exceptions.HTTPError:
        """
        url = "%s/api/v1/user/?format=json&email__iexact=%s" \
            % (SETTINGS.general.myTardisUrl,
               urllib.parse.quote(email.encode('utf-8')))
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
        response.raise_for_status()
        userRecordsJson = response.json()
        numUserRecordsFound = userRecordsJson['meta']['total_count']

        if numUserRecordsFound == 0:
            raise DoesNotExist(
                message="User with email \"%s\" was not found in MyTardis"
                % email,
                response=response)
        logger.debug("Found user record for email '" + email + "'.")
        return UserModel(userRecordJson=userRecordsJson['objects'][0])

    @staticmethod
    def GetUserForFolder(userFolderName, userNotFoundInMyTardis=False):
        """
        Return a UserModel for a username or email folder

        Set userNotFoundInMyTardis to True if you already know there is
        no corresponding user record in MyTardis, but you want to create
        a "USER NOT FOUND" dummy record to render in MyData's users table.
        """
        folderStructure = SETTINGS.advanced.folderStructure
        if folderStructure.startswith("Username"):
            if userNotFoundInMyTardis:
                return UserModel(
                    username=userFolderName, userNotFoundInMyTardis=True)
            return UserModel.GetUserByUsername(userFolderName)
        if folderStructure.startswith("Email"):
            if userNotFoundInMyTardis:
                return UserModel(
                    email=userFolderName, userNotFoundInMyTardis=True)
            return UserModel.GetUserByEmail(userFolderName)
        return None

class UserProfileModel(object):
    """
    Used with the DoesNotExist exception when a 404 from MyTardis's API
    is assumed to have been caused by a missing user profile record.
    """

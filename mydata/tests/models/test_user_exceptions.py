"""
Test ability to handle user-related exceptions.
"""
import os

from ...settings import SETTINGS
from ...models.user import UserModel
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import DoesNotExist
from .. import MyDataTester


class UserExceptionsTester(MyDataTester):
    """
    Test ability to handle user-related exceptions.
    """
    def setUp(self):
        super(UserExceptionsTester, self).setUp()
        super(UserExceptionsTester, self).InitializeAppAndFrame(
            'UserExceptionsTester')

    def test_user_exceptions(self):
        """
        Test ability to handle user-related exceptions.
        """
        pathToTestConfig = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataExpDataset.cfg"))
        self.assertTrue(os.path.exists(pathToTestConfig))
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataExpDataset.cfg"))
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        ValidateSettings()

        # Test retrieving default owner's user record (using UserModel's
        # GetUserByUsername method) and ensure that no exception is raised:
        owner = SETTINGS.defaultOwner

        # Test retrieving default owner's user record (using UserModel's
        # GetUserByEmail method) and ensure that no exception is raised:
        _ = UserModel.GetUserByEmail(owner.email)

        # Try to look up user record by username with an invalid API key,
        # which should give 401 (Unauthorized).
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = UserModel.GetUserByUsername(owner.username)
        SETTINGS.general.apiKey = apiKey

        # Try to look up user record by email with an invalid API key,
        # which should give 401 (Unauthorized).
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = UserModel.GetUserByEmail(owner.email)
        SETTINGS.general.apiKey = apiKey

        # Test Getters which act differently when the user folder name
        # can't be matched to a MyTardis user account:
        username = owner.username
        owner.username = None
        self.assertEqual(owner.username, UserModel.userNotFoundString)
        owner.username = username

        fullName = owner.fullName
        owner.fullName = None
        self.assertEqual(owner.fullName, UserModel.userNotFoundString)
        owner.fullName = fullName

        email = owner.email
        owner.email = None
        self.assertEqual(owner.email, UserModel.userNotFoundString)
        owner.email = email

        # GetValueForKey is used to display User field values
        # in the Users or Folders view:

        self.assertEqual(owner.GetValueForKey('email'), owner.email)

        email = owner.email
        owner.email = None
        owner.userNotFoundInMyTardis = True
        self.assertEqual(owner.GetValueForKey('email'),
                         UserModel.userNotFoundString)
        owner.userNotFoundInMyTardis = False
        owner.email = email

        self.assertIsNone(owner.GetValueForKey('invalid'))

        with self.assertRaises(DoesNotExist):
            _ = UserModel.GetUserByUsername("INVALID_USER")

        with self.assertRaises(DoesNotExist):
            _ = UserModel.GetUserByEmail("invalid@email.com")

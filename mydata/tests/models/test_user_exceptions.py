"""
Test ability to handle user-related exceptions.
"""
import os

from .. import MyDataTester
from ...models.user import UserModel
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import DoesNotExist


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
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataExpDataset.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataExpDataset.cfg")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        ValidateSettings(settingsModel)

        # Test retrieving default owner's user record (using UserModel's
        # GetUserByUsername method) and ensure that no exception is raised:
        owner = settingsModel.defaultOwner

        # Test retrieving default owner's user record (using UserModel's
        # GetUserByEmail method) and ensure that no exception is raised:
        _ = UserModel.GetUserByEmail(settingsModel, owner.email)

        # Try to look up user record by username with an invalid API key,
        # which should give 401 (Unauthorized).
        apiKey = settingsModel.general.apiKey
        settingsModel.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = UserModel.GetUserByUsername(settingsModel, owner.username)
        settingsModel.general.apiKey = apiKey

        # Try to look up user record by email with an invalid API key,
        # which should give 401 (Unauthorized).
        apiKey = settingsModel.general.apiKey
        settingsModel.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = UserModel.GetUserByEmail(settingsModel, owner.email)
        settingsModel.general.apiKey = apiKey

        # Test Getters which act differently when the user folder name
        # can't be matched to a MyTardis user account:
        username = owner.username
        owner.username = None
        self.assertEqual(owner.GetUsername(), UserModel.userNotFoundString)
        owner.username = username

        name = owner.name
        owner.name = None
        self.assertEqual(owner.GetName(), UserModel.userNotFoundString)
        owner.name = name

        email = owner.email
        owner.email = None
        self.assertEqual(owner.GetEmail(), UserModel.userNotFoundString)
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
            _ = UserModel.GetUserByUsername(settingsModel, "INVALID_USER")

        with self.assertRaises(DoesNotExist):
            _ = UserModel.GetUserByEmail(settingsModel, "invalid@email.com")

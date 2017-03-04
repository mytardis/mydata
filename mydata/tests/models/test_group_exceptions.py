"""
Test ability to handle group-related exceptions.
"""
import os

from .. import MyDataTester
from ...settings import SETTINGS
from ...models.group import GroupModel
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import DoesNotExist


class GroupExceptionsTester(MyDataTester):
    """
    Test ability to handle group-related exceptions.
    """
    def setUp(self):
        super(GroupExceptionsTester, self).setUp()
        super(GroupExceptionsTester, self).InitializeAppAndFrame(
            'GroupExceptionsTester')

    def test_group_exceptions(self):
        """
        Test ability to handle group-related exceptions.
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

        # Test retrieving a valid group record (using GroupModel's
        # GetGroupByName method) and ensure that no exception is raised:
        group = GroupModel.GetGroupByName("TestFacility-Group1")
        self.assertEqual(group.name, "TestFacility-Group1")
        self.assertEqual(group.GetValueForKey('name'), group.name)

        # Try to look up group record with an invalid API key,
        # which should give 401 (Unauthorized).
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = GroupModel.GetGroupByName("TestFacility-Group 1")
        SETTINGS.general.apiKey = apiKey

        with self.assertRaises(DoesNotExist):
            _ = GroupModel.GetGroupByName("INVALID_GROUP")

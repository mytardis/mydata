"""
Test ability to handle group-related exceptions.
"""
import os

from .. import MyDataTester
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

        # Test retrieving a valid group record (using GroupModel's
        # GetGroupByName method) and ensure that no exception is raised:
        group = GroupModel.GetGroupByName(settingsModel, "TestFacility-Group1")
        self.assertEqual(group.name, "TestFacility-Group1")
        self.assertEqual(group.GetValueForKey('name'), group.name)

        # Try to look up group record with an invalid API key,
        # which should give 401 (Unauthorized).
        apiKey = settingsModel.general.apiKey
        settingsModel.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = GroupModel.GetGroupByName(settingsModel, "TestFacility-Group 1")
        settingsModel.general.apiKey = apiKey

        myTardisUrl = settingsModel.general.myTardisUrl
        settingsModel.general.myTardisUrl = \
            "%s/request/http/code/404/" % myTardisUrl
        with self.assertRaises(DoesNotExist):
            _ = GroupModel.GetGroupByName(settingsModel, "TestFacility-Group 1")
        settingsModel.general.myTardisUrl = myTardisUrl

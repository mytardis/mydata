"""
Test ability to handle group-related exceptions.
"""
from requests.exceptions import HTTPError

from .. import MyDataTester
from ...settings import SETTINGS
from ...models.group import GroupModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import DoesNotExist


class GroupExceptionsTester(MyDataTester):
    """
    Test ability to handle group-related exceptions.
    """
    def test_group_exceptions(self):
        """Test ability to handle group-related exceptions.
        """
        self.UpdateSettingsFromCfg("testdataExpDataset")
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
        with self.assertRaises(HTTPError) as context:
            _ = GroupModel.GetGroupByName("TestFacility-Group 1")
        self.assertEqual(context.exception.response.status_code, 401)
        SETTINGS.general.apiKey = apiKey

        with self.assertRaises(DoesNotExist):
            _ = GroupModel.GetGroupByName("INVALID_GROUP")

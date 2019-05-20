"""
Test ability to handle ObjectACL-related exceptions.
"""
import os

from requests.exceptions import HTTPError

from ...settings import SETTINGS
from ...models.objectacl import ObjectAclModel
from ...models.experiment import ExperimentModel
from ...models.folder import FolderModel
from ...models.group import GroupModel
from ...models.settings.validation import ValidateSettings
from ...models.user import UserModel
from .. import MyDataTester


class ObjectAclExceptionsTester(MyDataTester):
    """
    Test ability to handle ObjectACL-related exceptions.
    """
    def test_objectacl_exceptions(self):
        """Test ability to handle ObjectACL-related exceptions.
        """
        self.UpdateSettingsFromCfg("testdataExpDataset")
        ValidateSettings()

        owner = SETTINGS.general.defaultOwner
        dataViewId = 1
        datasetFolderName = "Flowers"
        expFolderName = "Exp1"
        location = os.path.join(SETTINGS.general.dataDirectory, expFolderName)

        # Test sharing experiment with user, and ensure that no exception
        # is raised:
        userFolderName = owner.username
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")
        ObjectAclModel.ShareExperimentWithUser(experimentModel, owner)

        # Test sharing experiment with group, and ensure that no exception
        # is raised:
        groupModel = GroupModel.GetGroupByName("TestFacility-Group1")
        ObjectAclModel.ShareExperimentWithGroup(
            experimentModel, groupModel, isOwner=True)

        # Try to create a user ObjectACL record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(HTTPError) as context:
            ObjectAclModel.ShareExperimentWithUser(experimentModel, owner)
        self.assertEqual(context.exception.response.status_code, 401)
        SETTINGS.general.apiKey = apiKey

        # Try to create a group ObjectACL record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(HTTPError) as context:
            ObjectAclModel.ShareExperimentWithGroup(
                experimentModel, groupModel, isOwner=True)
        self.assertEqual(context.exception.response.status_code, 401)
        SETTINGS.general.apiKey = apiKey

        # Try to create a user ObjectACL record with
        # a user without a UserProfile, which should give 404
        userWithoutProfile = UserModel.GetUserByUsername("userwithoutprofile")
        SETTINGS.general.defaultOwner = userWithoutProfile
        SETTINGS.general.username = "userwithoutprofile"
        with self.assertRaises(HTTPError) as context:
            ObjectAclModel.ShareExperimentWithUser(experimentModel,
                                                   userWithoutProfile)
        self.assertEqual(context.exception.response.status_code, 404)

        # Try to create a group ObjectACL record with
        # a user without a UserProfile, which should give 404
        with self.assertRaises(HTTPError) as context:
            ObjectAclModel.ShareExperimentWithGroup(
                experimentModel, groupModel, isOwner=True)
        self.assertEqual(context.exception.response.status_code, 404)

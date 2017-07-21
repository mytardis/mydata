"""
Test ability to handle ObjectACL-related exceptions.
"""
import os

from ...settings import SETTINGS
from ...models.objectacl import ObjectAclModel
from ...models.experiment import ExperimentModel
from ...models.folder import FolderModel
from ...models.group import GroupModel
from ...models.settings.validation import ValidateSettings
from ...models.user import UserModel
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import DoesNotExist
from .. import MyDataTester


class ObjectAclExceptionsTester(MyDataTester):
    """
    Test ability to handle ObjectACL-related exceptions.
    """
    def setUp(self):
        super(ObjectAclExceptionsTester, self).setUp()
        super(ObjectAclExceptionsTester, self).InitializeAppAndFrame(
            'ObjectAclExceptionsTester')

    def test_objectacl_exceptions(self):
        """
        Test ability to handle ObjectACL-related exceptions.
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
        ObjectAclModel.ShareExperimentWithGroup(experimentModel, groupModel)

        # Try to create a user ObjectACL record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            ObjectAclModel.ShareExperimentWithUser(experimentModel, owner)
        SETTINGS.general.apiKey = apiKey

        # Try to create a group ObjectACL record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            ObjectAclModel.ShareExperimentWithGroup(experimentModel, groupModel)
        SETTINGS.general.apiKey = apiKey

        # Try to create a user ObjectACL record with
        # a user without a UserProfile, which should give 404 (DoesNotExist)
        userWithoutProfile = UserModel.GetUserByUsername("userwithoutprofile")
        SETTINGS.general.defaultOwner = userWithoutProfile
        SETTINGS.general.username = "userwithoutprofile"
        with self.assertRaises(DoesNotExist):
            ObjectAclModel.ShareExperimentWithUser(experimentModel,
                                                   userWithoutProfile)

        # Try to create a group ObjectACL record with
        # a user without a UserProfile, which should give 404 (DoesNotExist)
        with self.assertRaises(DoesNotExist):
            ObjectAclModel.ShareExperimentWithGroup(experimentModel,
                                                    groupModel)

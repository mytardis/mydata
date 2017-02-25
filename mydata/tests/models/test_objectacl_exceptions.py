"""
Test ability to handle ObjectACL-related exceptions.
"""
import os

from .. import MyDataTester
from ...models.objectacl import ObjectAclModel
from ...models.experiment import ExperimentModel
from ...models.folder import FolderModel
from ...models.group import GroupModel
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...models.user import UserModel
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import DoesNotExist


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
        # pylint: disable=too-many-locals
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

        owner = settingsModel.defaultOwner
        dataViewId = 1
        datasetFolderName = "Flowers"
        expFolderName = "Exp1"
        location = os.path.join(dataDirectory, expFolderName)

        # Test sharing experiment with user, and ensure that no exception
        # is raised:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        folderModel.SetExperimentTitle("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        ObjectAclModel.ShareExperimentWithUser(experimentModel, owner)

        # Test sharing experiment with group, and ensure that no exception
        # is raised:
        groupModel = GroupModel.GetGroupByName(settingsModel,
                                               "TestFacility-Group1")
        ObjectAclModel.ShareExperimentWithGroup(experimentModel, groupModel)

        # Try to create a user ObjectACL record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = folderModel.settingsModel.general.apiKey
        folderModel.settingsModel.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            ObjectAclModel.ShareExperimentWithUser(experimentModel, owner)
        folderModel.settingsModel.general.apiKey = apiKey

        # Try to create a group ObjectACL record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = folderModel.settingsModel.general.apiKey
        folderModel.settingsModel.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            ObjectAclModel.ShareExperimentWithGroup(experimentModel, groupModel)
        folderModel.settingsModel.general.apiKey = apiKey

        # Try to create a user ObjectACL record with
        # a user without a UserProfile, which should give 404 (DoesNotExist)
        userWithoutProfile = UserModel.GetUserByUsername(settingsModel,
                                                         "userwithoutprofile")
        experimentModel.settingsModel.defaultOwner = userWithoutProfile
        experimentModel.settingsModel.general.username = "userwithoutprofile"
        with self.assertRaises(DoesNotExist):
            ObjectAclModel.ShareExperimentWithUser(experimentModel,
                                                   userWithoutProfile)

        # Try to create a group ObjectACL record with
        # a user without a UserProfile, which should give 404 (DoesNotExist)
        with self.assertRaises(DoesNotExist):
            ObjectAclModel.ShareExperimentWithGroup(experimentModel,
                                                    groupModel)

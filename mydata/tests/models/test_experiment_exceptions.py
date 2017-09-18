"""
Test ability to handle experiment-related exceptions.
"""
import os

from ...settings import SETTINGS
from ...threads.flags import FLAGS
from .. import MyDataTester
from ...models.experiment import ExperimentModel
from ...models.folder import FolderModel
from ...models.schema import SchemaModel
from ...models.settings.validation import ValidateSettings
from ...models.user import UserProfileModel
from ...utils.exceptions import DoesNotExist
from ...utils.exceptions import MultipleObjectsReturned
from ...utils.exceptions import Unauthorized


class ExperimentExceptionsTester(MyDataTester):
    """
    Test ability to handle experiment-related exceptions.
    """
    def test_experiment_exceptions(self):
        """
        Test ability to handle experiment-related exceptions.
        """
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        self.UpdateSettingsFromCfg("testdataExpDataset")
        # MyData has the concept of a "default experiment",
        # which depends on the UUID of the MyData instance:
        SETTINGS.miscellaneous.uuid = "1234567890"
        ValidateSettings()

        uploaderName = SETTINGS.uploaderModel.name
        owner = SETTINGS.general.defaultOwner
        dataViewId = 1
        datasetFolderName = "Flowers"
        expFolderName = "Exp1"
        location = os.path.join(SETTINGS.general.dataDirectory, expFolderName)

        # LOOKING UP EXPERIMENTS

        # LOOKING UP EXPERIMENTS WITH TITLE SET MANUALLY

        # Try to look up nonexistent experiment record with
        # experiment title set manually, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.username
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = expFolderName
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s'"
            % (uploaderName, userFolderName, expFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.username
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")

        # Look up one of many existing experiment records with
        # experiment title set manually, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.username
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = "Multiple Existing Experiments"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment1")

        # Try to look up nonexistent experiment record with
        # experiment title set manually, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = expFolderName
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s'"
            % (uploaderName, groupFolderName, expFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")

        # Try to look up nonexistent experiment record with
        # experiment title set manually, and with a user folder
        # name, and a group folder name:
        userFolderName = owner.username
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = expFolderName
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s', '%s'"
            % (uploaderName, userFolderName, expFolderName,
               groupFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with a group folder
        # name, and a user folder name:
        userFolderName = owner.username
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")

        # Try to look up nonexistent experiment record with
        # experiment title set manually, with neither a user folder
        # name, nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = expFolderName
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', '%s'"
            % (uploaderName, expFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with neither a user folder
        # name, nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")

        # Try to look up experiment record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        SETTINGS.general.apiKey = apiKey

        # Try to look up experiment record with a missing UserProfile
        # for the authorizing user, which can result in a 404 from the
        # MyTardis API:
        folderModel.experimentTitle = "Missing UserProfile"
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), UserProfileModel)

        # Try to look up experiment record with a missing Schema,
        # which can result in a 404 from the MyTardis API:
        folderModel.experimentTitle = "Missing Schema"
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), SchemaModel)

        # Try to look up experiment record and handle a 404 of
        # unknown origin from the MyTardis API:
        folderModel.experimentTitle = "Unknown 404"
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), None)

        # LOOKING UP EXPERIMENTS WITH TITLE SET AUTOMATICALLY

        folderModel.experimentTitle = ""
        folderModel.experimentTitleSetManually = False

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.username
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s" % (uploaderName, userFolderName))

        # Look up existing experiment record with
        # experiment title set automatically, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.username
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        uploaderUuid = SETTINGS.miscellaneous.uuid
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        SETTINGS.miscellaneous.uuid = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")
        SETTINGS.miscellaneous.uuid = uploaderUuid

        # Look up one of many existing experiment records with
        # experiment title set automatically, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.username
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        uploaderUuid = SETTINGS.miscellaneous.uuid
        SETTINGS.miscellaneous.uuid = "Multiple Existing Experiments"
        with self.assertRaises(MultipleObjectsReturned) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        SETTINGS.miscellaneous.uuid = uploaderUuid

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s"
            % (uploaderName, groupFolderName))

        # Look up existing experiment record with
        # experiment title set automatically, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        uploaderUuid = SETTINGS.miscellaneous.uuid
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        SETTINGS.miscellaneous.uuid = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")
        SETTINGS.miscellaneous.uuid = uploaderUuid

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, and with a user folder
        # name and a group folder name:
        userFolderName = owner.username
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s'"
            % (uploaderName, userFolderName, groupFolderName))

        # Look up existing experiment record with
        # experiment title set automatically, and with a user folder
        # name and a group folder name:
        userFolderName = owner.username
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        uploaderUuid = SETTINGS.miscellaneous.uuid
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        SETTINGS.miscellaneous.uuid = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")
        SETTINGS.miscellaneous.uuid = uploaderUuid

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, with neither a user folder
        # name, nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message, "Experiment not found for '%s'." % uploaderName)

        # Look up existing experiment record with
        # experiment title set automatically, and with neither a user folder
        # name nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        uploaderUuid = SETTINGS.miscellaneous.uuid
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        SETTINGS.miscellaneous.uuid = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")
        SETTINGS.miscellaneous.uuid = uploaderUuid

        # CREATING EXPERIMENTS

        # Try to create an experiment with a title specified manually
        # and check that the title is correct:
        FLAGS.testRunRunning = False
        folderModel.experimentTitle = expFolderName
        experimentModel = \
            ExperimentModel.CreateExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, expFolderName)

        # Try to create an experiment with a title specified manually,
        # during a test run
        FLAGS.testRunRunning = True
        folderModel.experimentTitle = expFolderName
        experimentModel = \
            ExperimentModel.GetOrCreateExperimentForFolder(folderModel)
        self.assertEqual(experimentModel, None)
        FLAGS.testRunRunning = False

        # Get or create an experiment with a title specified manually,
        # which already exists during a test run
        FLAGS.testRunRunning = True
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = \
            ExperimentModel.GetOrCreateExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")
        folderModel.experimentTitle = expFolderName
        FLAGS.testRunRunning = False

        # Try to create an experiment record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = ExperimentModel.CreateExperimentForFolder(folderModel)
        SETTINGS.general.apiKey = apiKey

        # Now let's test experiment creation with the experiment's
        # title determined automatically (from the instrument's name
        # which becomes the default uploader name) and the user folder
        # name or group folder name):
        userFolderName = owner.username
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)

        # Test case where MyTardis API returns a 404, e.g. because a
        # requested Experiment Schema can't be found.
        folderModel.experimentTitle = "Request 404 from Fake MyTardis Server"
        with self.assertRaises(DoesNotExist):
            _ = ExperimentModel.CreateExperimentForFolder(folderModel)

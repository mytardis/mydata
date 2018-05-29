"""
Test ability to handle experiment-related exceptions.
"""
import os

from requests.exceptions import HTTPError

from ...settings import SETTINGS
from ...threads.flags import FLAGS
from .. import MyDataTester
from ...models.experiment import ExperimentModel
from ...models.folder import FolderModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import DoesNotExist


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

        owner = SETTINGS.general.defaultOwner
        dataViewId = 1
        datasetFolderName = "Flowers"
        expFolderName = "Exp1"
        location = os.path.join(SETTINGS.general.dataDirectory, expFolderName)

        # LOOKING UP EXPERIMENTS

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
        with self.assertRaises(HTTPError) as context:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(context.exception.response.status_code, 401)
        SETTINGS.general.apiKey = apiKey

        # Try to look up experiment record with a missing UserProfile
        # for the authorizing user, which can result in a 404 from the
        # MyTardis API:
        folderModel.experimentTitle = "Missing UserProfile"
        with self.assertRaises(HTTPError) as context:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(context.exception.response.status_code, 404)

        # Try to look up experiment record with a missing Schema,
        # which can result in a 404 from the MyTardis API:
        folderModel.experimentTitle = "Missing Schema"
        with self.assertRaises(HTTPError) as context:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(context.exception.response.status_code, 404)

        # Try to look up experiment record and handle a 404 of
        # unknown origin from the MyTardis API:
        folderModel.experimentTitle = "Unknown 404"
        with self.assertRaises(HTTPError) as context:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(context.exception.response.status_code, 404)

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
        with self.assertRaises(HTTPError) as context:
            _ = ExperimentModel.CreateExperimentForFolder(folderModel)
        self.assertEqual(context.exception.response.status_code, 401)
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
        with self.assertRaises(HTTPError) as context:
            _ = ExperimentModel.CreateExperimentForFolder(folderModel)
        self.assertEqual(context.exception.response.status_code, 404)

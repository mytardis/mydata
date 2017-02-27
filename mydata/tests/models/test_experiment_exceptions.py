"""
Test ability to handle experiment-related exceptions.
"""
import os

from .. import MyDataTester
from ...models.experiment import ExperimentModel
from ...models.folder import FolderModel
from ...models.schema import SchemaModel
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...models.user import UserProfileModel
from ...utils.exceptions import DoesNotExist
from ...utils.exceptions import MultipleObjectsReturned
from ...utils.exceptions import Unauthorized


class ExperimentExceptionsTester(MyDataTester):
    """
    Test ability to handle experiment-related exceptions.
    """
    def setUp(self):
        super(ExperimentExceptionsTester, self).setUp()
        super(ExperimentExceptionsTester, self).InitializeAppAndFrame(
            'ExperimentExceptionsTester')

    def test_experiment_exceptions(self):
        """
        Test ability to handle experiment-related exceptions.
        """
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
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

        # LOOKING UP EXPERIMENTS

        # LOOKING UP EXPERIMENTS WITH TITLE SET MANUALLY

        # Try to look up nonexistent experiment record with
        # experiment title set manually, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        folderModel.experimentTitle = expFolderName
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s'"
            % (instrument, userFolderName, expFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")

        # Look up one of many existing experiment records with
        # experiment title set manually, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        folderModel.experimentTitle = "Multiple Existing Experiments"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment1")

        # Try to look up nonexistent experiment record with
        # experiment title set manually, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        folderModel.experimentTitle = expFolderName
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s'"
            % (instrument, groupFolderName, expFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")

        # Try to look up nonexistent experiment record with
        # experiment title set manually, and with a user folder
        # name, and a group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        folderModel.experimentTitle = expFolderName
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s', '%s'"
            % (instrument, userFolderName, expFolderName,
               groupFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with a group folder
        # name, and a user folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")

        # Try to look up nonexistent experiment record with
        # experiment title set manually, with neither a user folder
        # name, nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        folderModel.experimentTitle = expFolderName
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', '%s'"
            % (instrument, expFolderName))

        # Look up existing experiment record with
        # experiment title set manually, and with neither a user folder
        # name, nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")

        # Try to look up experiment record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = folderModel.settingsModel.general.apiKey
        folderModel.settingsModel.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        folderModel.settingsModel.general.apiKey = apiKey

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
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s" % (instrument, userFolderName))

        # Look up existing experiment record with
        # experiment title set automatically, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        uploaderUuid = settingsModel.uploaderModel.GetUuid()
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        folderModel.settingsModel.uploaderModel.SetUuid("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        folderModel.settingsModel.uploaderModel.SetUuid(uploaderUuid)

        # Look up one of many existing experiment records with
        # experiment title set automatically, and with a user folder
        # name, but no group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        uploaderUuid = settingsModel.uploaderModel.GetUuid()
        folderModel.settingsModel.uploaderModel.SetUuid("Multiple Existing Experiments")
        with self.assertRaises(MultipleObjectsReturned) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        folderModel.settingsModel.uploaderModel.SetUuid(uploaderUuid)

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s"
            % (instrument, groupFolderName))

        # Look up existing experiment record with
        # experiment title set automatically, and with a group folder
        # name, but no user folder name:
        userFolderName = None
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        uploaderUuid = settingsModel.uploaderModel.GetUuid()
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        folderModel.settingsModel.uploaderModel.SetUuid("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        folderModel.settingsModel.uploaderModel.SetUuid(uploaderUuid)

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, and with a user folder
        # name and a group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message,
            "Experiment not found for '%s', %s, '%s'"
            % (instrument, userFolderName, groupFolderName))

        # Look up existing experiment record with
        # experiment title set automatically, and with a user folder
        # name and a group folder name:
        userFolderName = owner.GetUsername()
        groupFolderName = "Test Group1"
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        uploaderUuid = settingsModel.uploaderModel.GetUuid()
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        folderModel.settingsModel.uploaderModel.SetUuid("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        folderModel.settingsModel.uploaderModel.SetUuid(uploaderUuid)

        # Try to look up nonexistent experiment record with
        # experiment title set automatically, with neither a user folder
        # name, nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        instrument = settingsModel.instrument.GetName()
        with self.assertRaises(DoesNotExist) as contextManager:
            _ = ExperimentModel.GetExperimentForFolder(folderModel)
        exception = contextManager.exception
        self.assertEqual(exception.GetModelClass(), ExperimentModel)
        self.assertEqual(
            exception.message, "Experiment not found for '%s'." % instrument)

        # Look up existing experiment record with
        # experiment title set automatically, and with neither a user folder
        # name nor a group folder name:
        userFolderName = None
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)
        uploaderUuid = settingsModel.uploaderModel.GetUuid()
        # A trick to tell our Fake MyTardis server to return an existing experiment:
        folderModel.settingsModel.uploaderModel.SetUuid("Existing Experiment")
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        folderModel.settingsModel.uploaderModel.SetUuid(uploaderUuid)

        # CREATING EXPERIMENTS

        # Try to create an experiment with a title specified manually
        # and check that the title is correct:
        testRun = False
        folderModel.experimentTitle = expFolderName
        experimentModel = \
            ExperimentModel.CreateExperimentForFolder(folderModel, testRun)
        self.assertEqual(experimentModel.GetTitle(), expFolderName)

        # Try to create an experiment with a title specified manually,
        # and with testRun activated:
        testRun = True
        folderModel.experimentTitle = expFolderName
        experimentModel = \
            ExperimentModel.GetOrCreateExperimentForFolder(folderModel, testRun)
        self.assertEqual(experimentModel, None)
        testRun = False

        # Get or create an experiment with a title specified manually,
        # which already exists and with testRun activated:
        testRun = True
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = \
            ExperimentModel.GetOrCreateExperimentForFolder(folderModel, testRun)
        self.assertEqual(experimentModel.GetTitle(), "Existing Experiment")
        folderModel.experimentTitle = expFolderName
        testRun = False

        # Try to create an experiment record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = folderModel.settingsModel.general.apiKey
        folderModel.settingsModel.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = ExperimentModel.CreateExperimentForFolder(folderModel, testRun)
        folderModel.settingsModel.general.apiKey = apiKey

        # Now let's test experiment creation with the experiment's
        # title determined automatically (from the instrument's name
        # and user folder name or group folder name):
        userFolderName = owner.GetUsername()
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner, settingsModel)

        # Test case where MyTardis API returns a 404, e.g. because a
        # requested Experiment Schema can't be found.
        folderModel.experimentTitle = "Request 404 from Fake MyTardis Server"
        with self.assertRaises(DoesNotExist):
            _ = ExperimentModel.CreateExperimentForFolder(folderModel, testRun)

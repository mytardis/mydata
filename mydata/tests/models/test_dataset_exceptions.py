"""
Test ability to handle dataset-related exceptions.
"""
import os

from ...settings import SETTINGS
from .. import MyDataTester
from ...models.dataset import DatasetModel
from ...models.experiment import ExperimentModel
from ...models.folder import FolderModel
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import InternalServerError


class DatasetExceptionsTester(MyDataTester):
    """
    Test ability to handle dataset-related exceptions.
    """
    def setUp(self):
        super(DatasetExceptionsTester, self).setUp()
        super(DatasetExceptionsTester, self).InitializeAppAndFrame(
            'DatasetExceptionsTester')

    def test_dataset_exceptions(self):
        """
        Test ability to handle dataset-related exceptions.
        """
        # pylint: disable=too-many-locals
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

        owner = SETTINGS.defaultOwner
        dataViewId = 1
        datasetFolderName = "Flowers"
        expFolderName = "Exp1"
        location = os.path.join(dataDirectory, expFolderName)

        # Test creating dataset record and ensure that no exception
        # is raised:
        userFolderName = owner.username
        groupFolderName = None
        folderModel = \
            FolderModel(dataViewId, datasetFolderName, location,
                        userFolderName, groupFolderName, owner)
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        self.assertEqual(experimentModel.title, "Existing Experiment")
        folderModel.experimentModel = experimentModel
        testRun = False
        datasetModel = DatasetModel.CreateDatasetIfNecessary(folderModel, testRun)
        self.assertEqual(datasetModel.description, datasetFolderName)

        # Simulate creating dataset record with testRun True
        # and ensure that no exception is raised:
        testRun = True
        datasetModel = DatasetModel.CreateDatasetIfNecessary(folderModel, testRun)
        self.assertEqual(datasetModel, None)
        testRun = False

        # Simulate retrieving existing dataset record with testRun True
        # and ensure that no exception is raised:
        testRun = True
        folderModel.folderName = "Existing Dataset"
        datasetModel = DatasetModel.CreateDatasetIfNecessary(folderModel, testRun)
        self.assertEqual(datasetModel.description, "Existing Dataset")
        testRun = False

        # Try to look up dataset record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = DatasetModel.CreateDatasetIfNecessary(folderModel, testRun)
        SETTINGS.general.apiKey = apiKey

        # Try to create a new dataset record with the Fake MyTardis
        # server simulating the case where the user doesn't have
        # permission to do so.
        folderModel.folderName = "New Dataset Folder Without Permission"
        with self.assertRaises(Unauthorized):
            _ = DatasetModel.CreateDatasetIfNecessary(folderModel, testRun)

        # Try to create a new dataset record with the Fake MyTardis
        # server simulating the case where an Internal Server Error
        # occurs.
        folderModel.folderName = "New Dataset Folder With Internal Server Error"
        with self.assertRaises(InternalServerError):
            _ = DatasetModel.CreateDatasetIfNecessary(folderModel, testRun)

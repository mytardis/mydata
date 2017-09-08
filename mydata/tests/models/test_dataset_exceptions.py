"""
Test ability to handle dataset-related exceptions.
"""
import os

from ...settings import SETTINGS
from ...threads.flags import FLAGS
from .. import MyDataTester
from ...models.dataset import DatasetModel
from ...models.experiment import ExperimentModel
from ...models.folder import FolderModel
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
        self.UpdateSettingsFromCfg("testdataExpDataset")
        ValidateSettings()

        owner = SETTINGS.general.defaultOwner
        dataViewId = 1
        datasetFolderName = "Flowers"
        expFolderName = "Exp1"
        location = os.path.join(SETTINGS.general.dataDirectory, expFolderName)

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
        FLAGS.testRunRunning = False
        datasetModel = DatasetModel.CreateDatasetIfNecessary(folderModel)
        self.assertEqual(datasetModel.description, datasetFolderName)

        # Simulate creating dataset record during test run
        # and ensure that no exception is raised:
        FLAGS.testRunRunning = True
        datasetModel = DatasetModel.CreateDatasetIfNecessary(folderModel)
        self.assertEqual(datasetModel, None)
        FLAGS.testRunRunning = False

        # Simulate retrieving existing dataset record during test run
        # and ensure that no exception is raised:
        FLAGS.testRunRunning = True
        folderModel.folderName = "Existing Dataset"
        datasetModel = DatasetModel.CreateDatasetIfNecessary(folderModel)
        FLAGS.testRunRunning = False
        self.assertEqual(datasetModel.description, "Existing Dataset")

        # Try to look up dataset record with
        # an invalid API key, which should give 401 (Unauthorized)
        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = DatasetModel.CreateDatasetIfNecessary(folderModel)
        SETTINGS.general.apiKey = apiKey

        # Try to create a new dataset record with the Fake MyTardis
        # server simulating the case where the user doesn't have
        # permission to do so.
        folderModel.folderName = "New Dataset Folder Without Permission"
        with self.assertRaises(Unauthorized):
            _ = DatasetModel.CreateDatasetIfNecessary(folderModel)

        # Try to create a new dataset record with the Fake MyTardis
        # server simulating the case where an Internal Server Error
        # occurs.
        folderModel.folderName = "New Dataset Folder With Internal Server Error"
        with self.assertRaises(InternalServerError):
            _ = DatasetModel.CreateDatasetIfNecessary(folderModel)

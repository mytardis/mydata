"""
Test ability to create immutable datasets.
"""
import os

from ...settings import SETTINGS
from .. import MyDataTester
from ...models.dataset import DatasetModel
from ...models.experiment import ExperimentModel
from ...models.folder import FolderModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import DoesNotExist


class ImmutableDatasetsTester(MyDataTester):
    """
    Test ability to handle dataset-related exceptions.
    """
    def setUp(self):
        super(ImmutableDatasetsTester, self).setUp()
        super(ImmutableDatasetsTester, self).InitializeAppAndFrame(
            'ImmutableDatasetsTester')

    def test_immutable_datasets(self):
        """
        Test ability to create immutable datasets.
        """
        self.UpdateSettingsFromCfg("testdataExpDataset")
        ValidateSettings()

        owner = SETTINGS.general.defaultOwner
        dataViewId = 1
        datasetFolderName = "Flowers"
        expFolderName = "Exp1"
        location = os.path.join(SETTINGS.general.dataDirectory, expFolderName)

        # Test creating dataset record with immutable = False
        # and ensure that the created dataset record is not immutable:
        SETTINGS.miscellaneous.immutableDatasets = False
        userFolderName = owner.username
        groupFolderName = None
        folderModel = FolderModel(
            dataViewId, datasetFolderName, location, userFolderName,
            groupFolderName, owner)
        folderModel.experimentTitle = "Existing Experiment"
        experimentModel = ExperimentModel.GetExperimentForFolder(folderModel)
        folderModel.experimentModel = experimentModel
        with self.assertRaises(DoesNotExist):
            DatasetModel.GetDataset(folderModel)
        datasetModel = DatasetModel.CreateDatasetIfNecessary(folderModel)
        self.assertEqual(datasetModel.immutable, False)

        # Test creating dataset record with immutable = True
        # and ensure that the created dataset record is immutable:
        SETTINGS.miscellaneous.immutableDatasets = True
        # We are just using a fake MyTardis server, so it is possible
        # that a dataset doesn't exist, even though we just "created" it:
        with self.assertRaises(DoesNotExist):
            DatasetModel.GetDataset(folderModel)
        datasetModel = DatasetModel.CreateDatasetIfNecessary(folderModel)
        self.assertEqual(datasetModel.immutable, True)

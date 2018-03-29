"""
Model class for MyTardis API v1's DatasetResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""
import urllib
import json
import requests

from ..settings import SETTINGS
from ..threads.flags import FLAGS
from ..logs import logger
from ..utils.exceptions import DoesNotExist


class DatasetModel(object):
    """
    Client-side model for caching results of querying
    MyTardis's dataset model.
    """
    def __init__(self, datasetJson):
        self.json = datasetJson

    @property
    def datasetId(self):
        """
        Return the dataset ID
        """
        return self.json['id']

    @property
    def description(self):
        """
        Return the dataset's description
        """
        return self.json['description']

    @property
    def immutable(self):
        """
        Return True if the dataset is immutable
        """
        return self.json['immutable']

    @property
    def resourceUri(self):
        """
        Return the dataset's MyTardis API resource URI,
        e.g. /api/v1/dataset/1234/
        """
        return self.json['resource_uri']

    @property
    def viewUri(self):
        """
        Return the dataset's view URI, as used in the MyData class's
        OnMyTardis method.
        """
        return "dataset/%s" % self.json['id']

    @staticmethod
    def CreateDatasetIfNecessary(folderModel):
        """
        Create a dataset if we don't already have one for this folder.

        First we check if a suitable dataset already exists.
        """
        experiment = folderModel.experimentModel
        try:
            existingDataset = DatasetModel.GetDataset(folderModel)
            if FLAGS.testRunRunning:
                message = "ADDING TO EXISTING DATASET FOR FOLDER: %s\n" \
                    "    URL: %s/%s\n" \
                    "    Description: %s\n" \
                    "    In Experiment: %s/%s" \
                    % (folderModel.GetRelPath(), SETTINGS.general.myTardisUrl,
                       existingDataset.viewUri, existingDataset.description,
                       SETTINGS.general.myTardisUrl,
                       experiment.viewUri if experiment else "experiment/?")
                logger.testrun(message)
            return existingDataset
        except DoesNotExist:
            description = folderModel.folderName
            logger.debug("Creating dataset record for folder: " + description)
            myTardisUrl = SETTINGS.general.myTardisUrl
            experimentUri = experiment.resourceUri.replace(
                'mydata_experiment', 'experiment') if experiment else None
            datasetJson = {
                "instrument": SETTINGS.general.instrument.resourceUri,
                "description": description,
                "experiments": [experimentUri],
                "immutable": SETTINGS.miscellaneous.immutableDatasets}
            data = json.dumps(datasetJson)
            url = "%s/api/v1/dataset/" % myTardisUrl
            if FLAGS.testRunRunning:
                message = "CREATING NEW DATASET FOR FOLDER: %s\n" \
                    "    Description: %s" \
                    % (folderModel.GetRelPath(), description)
                if experiment:  # Could be None in test run.
                    message += "\n    In Experiment: %s/%s" \
                        % (SETTINGS.general.myTardisUrl, experiment.viewUri)
                logger.testrun(message)
                return None
            response = requests.post(headers=SETTINGS.defaultHeaders,
                                     url=url, data=data)
            response.raise_for_status()
            newDatasetJson = response.json()
            return DatasetModel(newDatasetJson)

    @staticmethod
    def GetDataset(folderModel):
        """
        Get the dataset record for this folder

        If multiple datasets are found matching the folder, we return the first
        one and log a warning.  We could raise a MultipleObjectsReturned
        exception, but generally it is better to ensure that the data is
        uploaded, rather than have MyData refuse to upload because a duplicate
        dataset has been created on the server.
        """
        if not folderModel.experimentModel:
            # folderModel.experimentModel could be None in testRun
            message = "Dataset can't exist because experiment is None"
            raise DoesNotExist(message, modelClass=DatasetModel)
        description = urllib.quote(folderModel.folderName.encode('utf-8'))
        url = ("%s/api/v1/dataset/?format=json&experiments__id=%s"
               "&description=%s" % (SETTINGS.general.myTardisUrl,
                                    folderModel.experimentModel.experimentId,
                                    description))
        urlWithInstrument = "%s&instrument__id=%s"\
            % (url, SETTINGS.general.instrument.instrumentId)
        response = requests.get(
            headers=SETTINGS.defaultHeaders, url=urlWithInstrument)
        if response.status_code == 400:
            logger.debug(
                "MyTardis doesn't support filtering datasets by instrument")
            response = requests.get(headers=SETTINGS.defaultHeaders, url=url)
        response.raise_for_status()
        datasetsJson = response.json()
        numDatasets = datasetsJson['meta']['total_count']
        if numDatasets == 0:
            message = "Didn't find dataset for folder %s" % description
            raise DoesNotExist(message, modelClass=DatasetModel)
        if numDatasets > 1:
            logger.warning(
                "WARNING: Found multiple datasets for folder %s" % description)
        if numDatasets == 1:
            logger.debug("Found existing dataset for folder %s" % description)
        return DatasetModel(datasetsJson['objects'][0])

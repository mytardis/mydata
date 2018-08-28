"""
Model class for MyTardis API v1's DataFileResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import io
import json
import urllib

import requests
from requests_toolbelt.multipart import encoder

from ..dataviewmodels.dataview import DATAVIEW_MODELS
from ..settings import SETTINGS
from ..logs import logger
from ..utils.exceptions import DoesNotExist
from ..utils.exceptions import MultipleObjectsReturned
from ..utils import UnderscoreToCamelcase
from .replica import ReplicaModel


class DataFileModel(object):
    """
    Model class for MyTardis API v1's DataFileResource.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, dataset, dataFileJson):
        self.json = dataFileJson
        self.datafileId = None
        self.filename = None
        self.directory = None
        self.size = None
        self.createdTime = None
        self.modificationTime = None
        self.mimetype = None
        self.md5sum = None
        self.sha512sum = None
        self.deleted = None
        self.deletedTime = None
        self.version = None
        self.replicas = []
        self.parameterSets = []
        if dataFileJson is not None:
            for key in dataFileJson:
                attr = UnderscoreToCamelcase(key)
                if attr == "id":
                    attr = "datafileId"
                if hasattr(self, attr):
                    self.__dict__[attr] = dataFileJson[key]
            self.replicas = []
            for replicaJson in dataFileJson['replicas']:
                self.replicas.append(ReplicaModel(replicaJson=replicaJson))
        # This needs to go after self.__dict__[key] = dataFileJson[key]
        # so we get the full dataset model, not just the API resource string:
        self.dataset = dataset

    @staticmethod
    def GetDataFile(dataset, filename, directory):
        """
        Lookup datafile by dataset, filename and directory.

        :raises requests.exceptions.HTTPError:
        """
        myTardisUrl = SETTINGS.general.myTardisUrl
        url = myTardisUrl + "/api/v1/mydata_dataset_file/?format=json" + \
            "&dataset__id=" + str(dataset.datasetId) + \
            "&filename=" + urllib.quote(filename.encode('utf-8')) + \
            "&directory=" + urllib.quote(directory.encode('utf-8'))
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
        response.raise_for_status()
        dataFilesJson = response.json()
        numDataFilesFound = dataFilesJson['meta']['total_count']
        if numDataFilesFound == 0:
            raise DoesNotExist(
                message="Datafile \"%s\" was not found in MyTardis" % filename,
                response=response)
        elif numDataFilesFound > 1:
            raise MultipleObjectsReturned(
                message="Multiple datafiles matching %s were found in MyTardis"
                % filename,
                response=response)
        else:
            return DataFileModel(
                dataset=dataset, dataFileJson=dataFilesJson['objects'][0])

    @staticmethod
    def GetDataFileFromId(dataFileId):
        """
        Lookup datafile by ID.

        :raises requests.exceptions.HTTPError:
        """
        myTardisUrl = SETTINGS.general.myTardisUrl
        url = "%s/api/v1/mydata_dataset_file/%s/?format=json" \
            % (myTardisUrl, dataFileId)
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
        response.raise_for_status()
        dataFileJson = response.json()
        return DataFileModel(dataset=None, dataFileJson=dataFileJson)

    @staticmethod
    def Verify(datafileId):
        """
        Verify a datafile via the MyTardis API.
        """
        myTardisUrl = SETTINGS.general.myTardisUrl
        url = myTardisUrl + "/api/v1/dataset_file/%s/verify/" % datafileId
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
        if response.status_code < 200 or response.status_code >= 300:
            logger.warning("Failed to verify datafile id \"%s\" " % datafileId)
            logger.warning(response.text)
        # Returning True doesn't mean that the file has been verified.
        # It just means that the MyTardis API has accepted our verification
        # request without raising an error.  The verification is asynchronous
        # so it might not happen immediately if there is congestion in the
        # Celery queue.
        return True

    @staticmethod
    def CreateDataFileForStagingUpload(dataFileDict):
        """
        Create a DataFile record and return a temporary URL to upload
        to (e.g. by SCP).
        """
        url = "%s/api/v1/mydata_dataset_file/" % SETTINGS.general.myTardisUrl
        dataFileJson = json.dumps(dataFileDict)
        response = requests.post(headers=SETTINGS.defaultHeaders,
                                 url=url, data=dataFileJson)
        return response

    @staticmethod
    def UploadDataFileWithPost(dataFilePath, dataFileDict,
                               uploadModel, progressCallback):
        """
        Upload a file to the MyTardis API via POST, creating a new
        DataFile record.
        """
        url = "%s/api/v1/mydata_dataset_file/" % SETTINGS.general.myTardisUrl
        message = "Initializing buffered reader..."
        DATAVIEW_MODELS['uploads'].SetMessage(uploadModel, message)
        datafileBufferedReader = io.open(dataFilePath, 'rb')
        uploadModel.bufferedReader = datafileBufferedReader

        encoded = encoder.MultipartEncoder(
            fields={"json_data": json.dumps(dataFileDict),
                    'attached_file': (uploadModel.filename,
                                      datafileBufferedReader,
                                      'application/octet-stream')})
        # Workaround for issue with httplib's hard-coded read size
        # of 8192 bytes which can lead to slow uploads, see:
        # http://toolbelt.readthedocs.io/en/latest/uploading-data.html
        # https://github.com/requests/toolbelt/issues/75
        multipartEncoderReadMethod = encoded.read
        encoded.read = lambda size: multipartEncoderReadMethod(1024*1024)

        multipart = encoder.MultipartEncoderMonitor(encoded, progressCallback)

        headers = SETTINGS.defaultHeaders
        headers['Content-Type'] = multipart.content_type
        response = requests.post(url, data=multipart, headers=headers)
        return response

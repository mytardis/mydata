"""
Monitor upload progress using RESTful API queries
"""
from datetime import datetime
import threading

import requests

from ..events.stop import ShouldCancelUpload
from ..models.datafile import DataFileModel
from ..models.replica import ReplicaModel
from ..models.upload import UploadStatus
from ..utils.exceptions import DoesNotExist
from ..utils.exceptions import MissingMyDataReplicaApiEndpoint


def MonitorProgress(progressPollInterval, uploadModel,
                    fileSize, monitoringProgress, progressCallback):
    """
    Monitor progress via RESTful queries.
    """
    if ShouldCancelUpload(uploadModel) or \
            (uploadModel.status != UploadStatus.IN_PROGRESS and
             uploadModel.status != UploadStatus.NOT_STARTED):
        return

    timer = threading.Timer(
        progressPollInterval, MonitorProgress,
        args=[progressPollInterval, uploadModel, fileSize,
              monitoringProgress, progressCallback])
    timer.start()
    if uploadModel.status == UploadStatus.NOT_STARTED:
        return
    if monitoringProgress.isSet():
        return
    monitoringProgress.set()
    if uploadModel.dfoId is None:
        if uploadModel.dataFileId is not None:
            try:
                dataFile = DataFileModel.GetDataFileFromId(
                    uploadModel.dataFileId)
                uploadModel.dfoId = dataFile.replicas[0].dfoId
            except DoesNotExist:
                # If the DataFile ID reported in the location header
                # after POSTing to the API doesn't exist yet, don't
                # worry, just check again later.
                pass
            except IndexError:
                # If the dataFile.replicas[0] DFO doesn't exist yet,
                # don't worry, just check again later.
                pass
    if uploadModel.dfoId:
        try:
            bytesUploaded = \
                ReplicaModel.CountBytesUploadedToStaging(uploadModel.dfoId)
            latestUpdateTime = datetime.now()
            # If this file already has a partial upload in staging,
            # progress and speed estimates can be misleading.
            uploadModel.SetLatestTime(latestUpdateTime)
            if bytesUploaded > uploadModel.bytesUploaded:
                uploadModel.SetBytesUploaded(bytesUploaded)
            progressCallback(bytesUploaded, fileSize)
        except requests.exceptions.RequestException:
            timer.cancel()
        except MissingMyDataReplicaApiEndpoint:
            timer.cancel()
    monitoringProgress.clear()

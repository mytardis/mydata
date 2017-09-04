"""
Methods for copying files into a locally accessible file store
(e.g. an NFS Mount).
"""
from datetime import datetime
import os
import threading
from shutil import copy

import wx

from ..settings import SETTINGS
from ..threads.locks import LOCKS
from ..logs import logger

from .progress import MonitorProgress


def CopyFile(filePath, fileSize, targetFilePath,
             progressCallback, uploadModel):
    """
    Copy a file to a local directory or mount point.
    """
    bytesUploaded = 0
    progressCallback(bytesUploaded, fileSize, message="Uploading...")
    progressPollInterval = SETTINGS.miscellaneous.progressPollInterval
    monitoringProgress = threading.Event()
    uploadModel.startTime = datetime.now()
    MonitorProgress(progressPollInterval, uploadModel,
                    fileSize, monitoringProgress, progressCallback)
    targetDir = os.path.dirname(targetFilePath)
    with LOCKS.createDir:
        if targetDir not in REMOTE_DIRS_CREATED:
            if not os.path.exists(targetDir):
                os.makedirs(targetDir)
            REMOTE_DIRS_CREATED[targetDir] = True

    if wx.GetApp().foldersController.canceled or uploadModel.canceled:
        logger.debug("CopyFile: Aborting upload "
                     "for %s" % filePath)
        return

    targetDir = os.path.dirname(targetFilePath)
    copy(filePath, targetDir)
    latestUpdateTime = datetime.now()
    uploadModel.SetLatestTime(latestUpdateTime)
    bytesUploaded = fileSize
    progressCallback(bytesUploaded, fileSize)


REMOTE_DIRS_CREATED = dict()

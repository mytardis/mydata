import os
import threading
import urllib
import urllib2
import requests
import json
import Queue
import io
import poster
import traceback

from ExperimentModel import ExperimentModel
from DatasetModel import DatasetModel
from UploadModel import UploadModel
from UploadModel import UploadStatus
from FolderModel import FolderModel

from FoldersModel import GetFolderTypes

from logger.Logger import logger

import wx
import wx.lib.newevent
import wx.dataview

from DragAndDrop import MyFolderDropTarget
from AddFolderDialog import AddFolderDialog


class ConnectionStatus():
    CONNECTED = 0
    DISCONNECTED = 1


class FoldersController():

    def __init__(self, notifyWindow, foldersModel, foldersView, usersModel,
                 uploadsModel, settingsModel):

        self.notifyWindow = notifyWindow
        self.foldersModel = foldersModel
        self.foldersView = foldersView
        self.usersModel = usersModel
        self.uploadsModel = uploadsModel
        self.settingsModel = settingsModel

        self.verifyDatafileRunnable = {}
        self.verificationsQueue = Queue.Queue()
        self.verificationWorkerThreads = []
        self.numVerificationWorkerThreads = 25

        self.uploadDatafileRunnable = {}
        self.uploadsQueue = Queue.Queue()
        self.uploadWorkerThreads = []
        self.numUploadWorkerThreads = 5

        self.shuttingDown = False

        self.lastUsedFolderType = None
        self.folderDropTarget = MyFolderDropTarget(self)
        self.foldersView.SetDropTarget(self.folderDropTarget)

        self.foldersView.Bind(wx.EVT_BUTTON, self.OnOpenFolder,
                              self.foldersView.GetOpenFolderButton())
        self.foldersView.GetDataViewControl()\
            .Bind(wx.dataview.EVT_DATAVIEW_ITEM_ACTIVATED, self.OnOpenFolder)

        self.DidntFindMatchingDatafileOnServerEvent, \
            self.EVT_DIDNT_FIND_MATCHING_DATAFILE_ON_SERVER = \
            wx.lib.newevent.NewEvent()
        self.notifyWindow\
            .Bind(self.EVT_DIDNT_FIND_MATCHING_DATAFILE_ON_SERVER,
                  self.UploadDatafile)

        self.ConnectionStatusEvent, \
            self.EVT_CONNECTION_STATUS = wx.lib.newevent.NewEvent()
        self.notifyWindow.Bind(self.EVT_CONNECTION_STATUS,
                               self.UpdateStatusBar)

        for i in range(self.numUploadWorkerThreads):
            t = threading.Thread(target=self.uploadWorker, args=(self,))
            self.uploadWorkerThreads.append(t)
            t.start()

        for i in range(self.numVerificationWorkerThreads):
            t = threading.Thread(target=self.verificationWorker,
                                 args=(self, i+1))
            self.verificationWorkerThreads.append(t)
            t.start()

    def UpdateStatusBar(self, event):
        if event.connectionStatus == ConnectionStatus.CONNECTED:
            self.notifyWindow.SetConnected(event.myTardisUrl, True)
        else:
            self.notifyWindow.SetConnected(event.myTardisUrl, False)

    def UploadDatafile(self, event):
        folderModel = event.folderModel
        foldersController = event.foldersController
        dfi = event.dataFileIndex
        uploadsModel = foldersController.uploadsModel

        if folderModel not in foldersController.uploadDatafileRunnable:
            foldersController.uploadDatafileRunnable[folderModel] = {}

        uploadId = uploadsModel.GetMaxId() + 1
        uploadModel = UploadModel(uploadId, folderModel, dfi)
        uploadsModel.AddRow(uploadModel)
        foldersController.uploadDatafileRunnable[folderModel][dfi] = \
            UploadDatafileRunnable(self, self.foldersModel, folderModel,
                                   dfi, self.uploadsModel, uploadModel,
                                   self.settingsModel)
        self.uploadsQueue.put(foldersController
                              .uploadDatafileRunnable[folderModel][dfi])

    def StartDataUploads(self, folderModels=[]):
        class UploadDataThread(threading.Thread):
            def __init__(self, foldersController, foldersModel, settingsModel,
                         folderModels=[]):
                threading.Thread.__init__(self)
                self.foldersController = foldersController
                self.foldersModel = foldersModel
                self.settingsModel = settingsModel
                self.folderModels = folderModels

            def run(self):
                try:
                    if len(folderModels) == 0:
                        # Scan all folders
                        for row in range(0, self.foldersModel.GetRowCount()):
                            if self.foldersController.shuttingDown:
                                break
                            folderModel = self.foldersModel.foldersData[row]
                            if self.foldersController.shuttingDown:
                                break
                            if self.foldersController.shuttingDown:
                                break
                            try:
                                # Save MyTardis URL, so if it's changing in the
                                # Settings Dialog while this thread is
                                # attempting to connect, we ensure that any
                                # exception thrown by this thread refers to the
                                # old version of the URL.
                                myTardisUrl = \
                                    self.settingsModel.GetMyTardisUrl()
                                experimentModel = ExperimentModel\
                                    .GetExperimentForFolder(folderModel)
                                folderModel.SetExperiment(experimentModel)
                                CONNECTED = ConnectionStatus.CONNECTED
                                wx.PostEvent(
                                    self.foldersController.notifyWindow,
                                    self.foldersController.ConnectionStatusEvent(
                                        myTardisUrl=myTardisUrl,
                                        connectionStatus=CONNECTED))
                                datasetModel = DatasetModel\
                                    .CreateDatasetIfNecessary(folderModel)
                                folderModel.SetDatasetModel(datasetModel)
                                self.foldersController.VerifyDatafiles(folderModel)
                            except requests.exceptions.ConnectionError, e:
                                if not self.foldersController.shuttingDown:
                                    DISCONNECTED = \
                                        ConnectionStatus.DISCONNECTED
                                    wx.PostEvent(
                                        self.foldersController.notifyWindow,
                                        self.foldersController.ConnectionStatusEvent(
                                            myTardisUrl=myTardisUrl,
                                            connectionStatus=DISCONNECTED))
                            except ValueError, e:
                                logger.debug("Failed to retrieve experiment "
                                             "for folder " +
                                             str(folderModel.GetFolder()))
                                logger.debug(traceback.format_exc())
                                return
                            if experimentModel is None:
                                logger.debug("Failed to acquire a MyTardis "
                                             "experiment to store data in for"
                                             "folder " +
                                             folderModel.GetFolder())
                                return
                            if self.foldersController.shuttingDown:
                                break
                    else:
                        # Scan specific folders (e.g. dragged and dropped),
                        # instead of all of them:
                        for folderModel in folderModels:
                            if self.foldersController.shuttingDown:
                                break
                            folderModel.SetCreatedDate()
                            if self.foldersController.shuttingDown:
                                break
                            try:
                                # Save MyTardis URL, so if it's changing in the
                                # Settings Dialog while this thread is
                                # attempting to connect, we ensure that any
                                # exception thrown by this thread refers to the
                                # old version of the URL.
                                myTardisUrl = \
                                    self.settingsModel.GetMyTardisUrl()
                                experimentModel = ExperimentModel\
                                    .GetExperimentForFolder(folderModel)
                                folderModel.SetExperiment(experimentModel)
                                CONNECTED = ConnectionStatus.CONNECTED
                                wx.PostEvent(
                                    self.foldersController.notifyWindow,
                                    self.foldersController.ConnectionStatusEvent(
                                        myTardisUrl=myTardisUrl,
                                        connectionStatus=CONNECTED))
                                datasetModel = DatasetModel\
                                    .CreateDatasetIfNecessary(folderModel)
                                if self.foldersController.shuttingDown:
                                    break
                                folderModel.SetDatasetModel(datasetModel)
                                self.foldersController.VerifyDatafiles(folderModel)
                            except requests.exceptions.ConnectionError, e:
                                if not self.foldersController.shuttingDown:
                                    DISCONNECTED = \
                                        ConnectionStatus.DISCONNECTED
                                    wx.PostEvent(
                                        self.foldersController.notifyWindow,
                                        self.foldersController.ConnectionStatusEvent(
                                            myTardisUrl=myTardisUrl,
                                            connectionStatus=DISCONNECTED))
                            except ValueError, e:
                                logger.debug("Failed to retrieve experiment "
                                             "for folder " +
                                             str(folderModel.GetFolder()))
                                return
                            if self.foldersController.shuttingDown:
                                break
                except:
                    logger.error(traceback.format_exc())

        self.uploadDataThread = \
            UploadDataThread(foldersController=self,
                             foldersModel=self.foldersModel,
                             settingsModel=self.foldersModel.settingsModel,
                             folderModels=folderModels)
        self.uploadDataThread.start()


    def uploadWorker(self, foldersController):
        """
        One worker per thread
        By default, up to 5 threads can run simultaneously
        for uploading local data files to
        the MyTardis server.
        """
        while True:
            if foldersController.shuttingDown:
                break
            task = self.uploadsQueue.get()
            if task is None:
                break
            task.run()
            self.uploadsQueue.task_done()

    def verificationWorker(self, foldersController, verificationWorkerId):
        """
        One worker per thread.
        By default, up to 5 threads can run simultaneously
        for verifying whether local data files exist on
        the MyTardis server.
        """
        while True:
            if foldersController.shuttingDown:
                break
            task = self.verificationsQueue.get()
            if task is None:
                break
            task.run()
            self.verificationsQueue.task_done()

    def CleanUp(self):

        self.shuttingDown = True

        self.uploadsModel.CancelAll()

        if hasattr(self, 'uploadDataThread'):
            logger.debug("Joining FoldersController's UploadDataThread...")
            self.uploadDataThread.join()
            logger.debug("Joined FoldersController's UploadDataThread.")

        logger.debug("Shutting down FoldersController upload worker threads.")
        for i in range(self.numUploadWorkerThreads):
            self.uploadsQueue.put(None)
        for t in self.uploadWorkerThreads:
            t.join()

        logger.debug("Shutting down FoldersController verification "
                     "worker threads.")
        for i in range(self.numVerificationWorkerThreads):
            self.verificationsQueue.put(None)
        for t in self.verificationWorkerThreads:
            t.join()

    def OnDropFiles(self, filepaths):
        if len(filepaths) == 1 and self.foldersModel.Contains(filepaths[0]):
            message = "This folder has already been added."
            dlg = wx.MessageDialog(None, message, "Add Folder(s)",
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            return
        allFolders = True
        folderType = None
        folderModelsAdded = []
        for filepath in filepaths:
            import os
            if not os.path.isdir(filepath):
                message = filepath + " is not a folder."
                dlg = wx.MessageDialog(None, message, "Add Folder(s)",
                                       wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                return
            elif not self.foldersModel.Contains(filepath):
                (location, folder) = os.path.split(filepath)

                id = self.foldersModel.GetMaxId() + 1
                if folderType is None:

                    usersModel = self.usersModel
                    addFolderDialog = \
                        AddFolderDialog(self.notifyWindow, -1,
                                        "Add Folder(s)", usersModel,
                                        size=(350, 200),
                                        style=wx.DEFAULT_DIALOG_STYLE)
                    if self.lastUsedFolderType is not None:
                        addFolderDialog\
                            .SetFolderType(GetFolderTypes()
                                           .index(self.lastUsedFolderType))

                    addFolderDialog.CenterOnParent()

                    if addFolderDialog.ShowModal() == wx.ID_OK:
                        folderType = addFolderDialog.GetFolderType()
                        self.lastUsedFolderType = folderType
                    else:
                        return

                usersModel = self.usersModel
                owner = \
                    usersModel.GetUserByName(addFolderDialog.GetOwnerName())
                settingsModel = self.foldersModel.GetSettingsModel()
                folderModel = FolderModel(id=id, folder=folder,
                                          location=location,
                                          folder_type=self.lastUsedFolderType,
                                          owner_id=owner.GetId(),
                                          foldersModel=self.foldersModel,
                                          usersModel=usersModel,
                                          settingsModel=settingsModel)
                self.foldersModel.AddRow(folderModel)
                folderModelsAdded.append(folderModel)

        self.StartDataUploads(folderModels=folderModelsAdded)

    def VerifyDatafiles(self, folderModel):

        if folderModel not in self.verifyDatafileRunnable:
            self.verifyDatafileRunnable[folderModel] = []
        for dfi in range(0, folderModel.numFiles):

            if self.shuttingDown:
                break
            thisFileIsAlreadyBeingVerified = False
            for existingVerifyDatafileRunnable in \
                    self.verifyDatafileRunnable[folderModel]:
                if dfi == existingVerifyDatafileRunnable.GetDatafileIndex():
                    thisFileIsAlreadyBeingVerified = True

            thisFileIsAlreadyBeingUploaded = False
            if folderModel in self.uploadDatafileRunnable:
                if dfi in self.uploadDatafileRunnable[folderModel]:
                    thisFileIsAlreadyBeingUploaded = True

            if not thisFileIsAlreadyBeingVerified \
                    and not thisFileIsAlreadyBeingUploaded:
                self.verifyDatafileRunnable[folderModel]\
                    .append(VerifyDatafileRunnable(self, self.foldersModel,
                                                   folderModel, dfi,
                                                   self.settingsModel))
                self.verificationsQueue\
                    .put(self.verifyDatafileRunnable[folderModel][dfi])

    def Refresh(self):

        self.uploadsModel.CancelAll()

        self.verifyDatafileRunnable = {}
        self.uploadDatafileRunnable = {}

    def OnAddFolder(self, evt):
        dlg = wx.DirDialog(self.notifyWindow, "Choose a directory:")
        if dlg.ShowModal() == wx.ID_OK:
            self.OnDropFiles([dlg.GetPath(), ])

    def OnDeleteFolders(self, evt):
        # Remove the selected row(s) from the model. The model will take care
        # of notifying the view (and any other observers) that the change has
        # happened.
        items = self.foldersView.GetDataViewControl().GetSelections()
        rows = [self.foldersModel.GetRow(item) for item in items]
        if len(rows) > 1:
            message = "Are you sure you want to remove the selected folders?"
        elif len(rows) == 1:
            message = "Are you sure you want to remove the \"" + \
                self.foldersModel.GetValueForRowColname(rows[0], "Folder") + \
                "\" folder?"
        else:
            dlg = wx.MessageDialog(self.notifyWindow,
                                   "Please select a folder to delete.",
                                   "Delete Folder(s)", wx.OK)
            dlg.ShowModal()
            return
        confirmationDialog = \
            wx.MessageDialog(self.notifyWindow, message, "Confirm Delete",
                             wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        okToDelete = confirmationDialog.ShowModal()
        if okToDelete == wx.ID_OK:
            self.foldersModel.DeleteRows(rows)

    def OnOpenFolder(self, evt):
        items = self.foldersView.GetDataViewControl().GetSelections()
        rows = [self.foldersModel.GetRow(item) for item in items]
        if len(rows) != 1:
            if len(rows) > 1:
                message = "Please select a single folder."
            else:
                message = "Please select a folder to open."
            dlg = wx.MessageDialog(self.notifyWindow, message, "Open Folder",
                                   wx.OK)
            dlg.ShowModal()
            return
        row = rows[0]

        import os

        path = os.path.join(self.foldersModel
                            .GetValueForRowColname(row, "Location"),
                            self.foldersModel
                            .GetValueForRowColname(row, "Folder"))
        if not os.path.exists(path):
            message = "Path doesn't exist: " + path
            dlg = wx.MessageDialog(None, message, "Open Folder", wx.OK)
            dlg.ShowModal()
            return
        import subprocess
        import sys
        if sys.platform == 'darwin':
            def openFolder(path):
                subprocess.check_call(['open', '--', path])
        elif sys.platform.startswith('linux'):
            def openFolder(path):
                subprocess.check_call(['xdg-open', '--', path])
        elif sys.platform.startswith('win'):
            def openFolder(path):
                subprocess.call(['explorer', path])
        else:
            logger.debug("sys.platform = " + sys.platform)

        openFolder(path)


class VerifyDatafileRunnable():
    def __init__(self, foldersController, foldersModel, folderModel,
                 dataFileIndex, settingsModel):
        self.foldersController = foldersController
        self.foldersModel = foldersModel
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.settingsModel = settingsModel

    def GetDatafileIndex(self):
        return self.dataFileIndex

    def run(self):
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileDirectory = \
            self.folderModel.GetDataFileDirectory(self.dataFileIndex)
        dataFileName = os.path.basename(dataFilePath)
        datasetId = self.folderModel.GetDatasetModel().GetId()

        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        myTardisUsername = self.settingsModel.GetUsername()
        myTardisApiKey = self.settingsModel.GetApiKey()

        url = myTardisUrl + \
            "/api/v1/dataset_file/?format=json&dataset__id=" + str(datasetId)
        url = url + "&filename=" + urllib.quote(dataFileName)
        url = url + "&directory=" + urllib.quote(dataFileDirectory)

        headers = {"Authorization": "ApiKey " +
                   myTardisUsername + ":" + myTardisApiKey}

        response = requests.get(headers=headers, url=url)
        existingMatchingDataFiles = response.json()
        numExistingMatchingDataFiles = \
            existingMatchingDataFiles['meta']['total_count']

        if numExistingMatchingDataFiles == 1:

            self.folderModel.SetDataFileUploaded(self.dataFileIndex, True)
            self.foldersModel.FolderStatusUpdated(self.folderModel)

        elif numExistingMatchingDataFiles > 1:

            logger.debug("WARNING: Found multiple datafile uploads for " +
                         dataFilePath)

            self.folderModel.SetDataFileUploaded(self.dataFileIndex, True)
            self.foldersModel.FolderStatusUpdated(self.folderModel)

        if numExistingMatchingDataFiles == 0:
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.DidntFindMatchingDatafileOnServerEvent(
                    foldersController=self.foldersController,
                    folderModel=self.folderModel,
                    dataFileIndex=self.dataFileIndex))


class UploadDatafileRunnable():
    def __init__(self, foldersController, foldersModel, folderModel,
                 dataFileIndex, uploadsModel, uploadModel, settingsModel):
        self.foldersController = foldersController
        self.foldersModel = foldersModel
        self.folderModel = folderModel
        self.dataFileIndex = dataFileIndex
        self.uploadsModel = uploadsModel
        self.uploadModel = uploadModel
        self.settingsModel = settingsModel

    def GetDatafileIndex(self):
        return self.dataFileIndex

    def run(self):
        if self.uploadModel.Canceled():
            logger.debug("Upload for \"%s\" was canceled "
                         "before it began uploading." %
                         self.uploadModel.GetRelativePathToUpload())
            return
        dataFilePath = self.folderModel.GetDataFilePath(self.dataFileIndex)
        dataFileName = os.path.basename(dataFilePath)
        dataFileDirectory = \
            self.folderModel.GetDataFileDirectory(self.dataFileIndex)
        datasetId = self.folderModel.GetDatasetModel().GetId()

        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        myTardisUsername = self.settingsModel.GetUsername()
        myTardisApiKey = self.settingsModel.GetApiKey()

        logger.debug("Uploading " +
                     self.folderModel.GetDataFileName(self.dataFileIndex) +
                     "...")

        dataFileMd5Sum = md5sum(dataFilePath)
        dataFileSize = self.folderModel.GetDataFileSize(self.dataFileIndex)

        self.uploadModel.SetFileSize(dataFileSize)

        if self.uploadModel.Canceled():
            logger.debug("Upload for \"%s\" was canceled "
                         "before it began uploading." %
                         self.uploadModel.GetRelativePathToUpload())
            return
        if dataFileSize == 0:
            self.uploadsModel.UploadFileSizeUpdated(self.uploadModel)
            self.uploadModel.SetMessage("MyTardis will not accept a "
                                        "data file with a size of zero.")
            self.uploadsModel.UploadMessageUpdated(self.uploadModel)
            self.uploadModel.SetStatus(UploadStatus.FAILED)
            self.uploadsModel.UploadStatusUpdated(self.uploadModel)
            return

        import mimetypes
        dataFileMimeType = mimetypes.guess_type(dataFilePath)[0]
        datasetUri = self.folderModel.GetDatasetModel().GetResourceUri()
        dataFileJson = {"dataset": datasetUri, "filename": dataFileName,
                        "directory": dataFileDirectory,
                        "md5sum": dataFileMd5Sum, "size": dataFileSize,
                        "mimetype": dataFileMimeType}

        url = myTardisUrl + "/api/v1/dataset_file/"
        headers = {"Authorization": "ApiKey " + myTardisUsername + ":" +
                   myTardisApiKey}
        if self.uploadModel.Canceled():
            logger.debug("Upload for \"%s\" was canceled "
                         "before it began uploading." %
                         self.uploadModel.GetRelativePathToUpload())
            return
        datafileBufferedReader = io.open(dataFilePath, 'rb')
        self.uploadModel.SetBufferedReader(datafileBufferedReader)

        def prog_callback(param, current, total):
            if self.uploadModel.Canceled():
                return
            percentComplete = 100 - ((total - current) * 100) / (total)

            self.uploadModel.SetProgress(float(percentComplete))
            self.uploadsModel.UploadProgressUpdated(self.uploadModel)
            myTardisUrl = self.settingsModel.GetMyTardisUrl()
            wx.PostEvent(
                self.foldersController.notifyWindow,
                self.foldersController.ConnectionStatusEvent(
                    myTardisUrl=myTardisUrl,
                    connectionStatus=ConnectionStatus.CONNECTED))

        uploadToStagingRequest = self.settingsModel.GetUploadToStagingRequest()
        if uploadToStagingRequest['approved']:
            logger.info("Uploads via staging have been approved.")
        else:
            logger.info("Uploads via staging have not yet been approved.")

        datagen, headers = poster.encode.multipart_encode(
            {"json_data": json.dumps(dataFileJson),
             "attached_file": datafileBufferedReader},
            cb=prog_callback)

        opener = poster.streaminghttp.register_openers()

        opener.addheaders = [('Authorization', 'ApiKey ' + myTardisUsername +
                              ':' + myTardisApiKey)]

        success = False
        try:
            req = urllib2.Request(url, datagen, headers)
            try:
                response = urllib2.urlopen(req)
                # print str(req.header_items())
                success = True
            except ValueError, e:
                self.uploadModel.SetMessage(str(e))
                self.uploadsModel.UploadMessageUpdated(self.uploadModel)
                self.uploadModel.SetStatus(UploadStatus.FAILED)
                self.uploadsModel.UploadStatusUpdated(self.uploadModel)
                if str(e) == "read of closed file" or \
                        str(e) == "seek of closed file":
                    logger.debug("Aborting upload for \"%s\" because "
                                 "file handle was closed." %
                                 self.uploadModel.GetRelativePathToUpload())
                    return
                logger.error(traceback.format_exc())
        except urllib2.HTTPError, e:
            if not self.foldersController.shuttingDown:
                wx.PostEvent(
                    self.foldersController.notifyWindow,
                    self.foldersController.ConnectionStatusEvent(
                        myTardisUrl=self.settingsModel.GetMyTardisUrl(),
                        connectionStatus=ConnectionStatus.DISCONNECTED))

            self.uploadModel.SetMessage(str(e))
            self.uploadsModel.UploadMessageUpdated(self.uploadModel)
            self.uploadModel.SetStatus(UploadStatus.FAILED)
            self.uploadsModel.UploadStatusUpdated(self.uploadModel)
            if dataFileDirectory != "":
                logger.debug("Upload failed for datafile " + dataFileName +
                             " in subdirectory " + dataFileDirectory +
                             " of folder " + self.folderModel.GetFolder())
            else:
                logger.debug("Upload failed for datafile " + dataFileName +
                             " of folder " + self.folderModel.GetFolder())
            logger.debug(e.code)
            logger.debug(str(e))
            self.uploadModel.SetMessage(str(e))
            self.uploadsModel.UploadMessageUpdated(self.uploadModel)
            logger.debug(e.headers)
            logger.debug(e.fp.read())
            logger.debug(traceback.format_exc())

        if success:
            self.uploadModel.SetStatus(UploadStatus.COMPLETED)
            self.uploadsModel.UploadStatusUpdated(self.uploadModel)
            logger.debug("Upload succeeded for " + dataFilePath)

            self.uploadModel.SetProgress(100.0)
            self.uploadsModel.UploadProgressUpdated(self.uploadModel)
            self.folderModel.SetDataFileUploaded(self.dataFileIndex,
                                                 uploaded=True)
            self.foldersModel.FolderStatusUpdated(self.folderModel)
        else:
            self.uploadModel.SetProgress(0.0)
            logger.debug("Upload failed for " + dataFilePath)
            self.folderModel.SetDataFileUploaded(self.dataFileIndex,
                                                 uploaded=False)
            self.foldersModel.FolderStatusUpdated(self.folderModel)


def md5sum(filename, chunk_size=8192):
    import hashlib
    md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        # Note that the iter() func needs an empty byte string
        # for the returned iterator to halt at EOF, since read()
        # returns b'' (not just '').
        for chunk in iter(lambda: f.read(chunk_size), b''):
            md5.update(chunk)
    return md5.hexdigest()

"""
Represents the Folders tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import collections
import threading
import os
import sys
import traceback
from datetime import datetime
from glob import glob

import wx

from ..settings import SETTINGS
from ..models.folder import FolderModel
from ..models.user import UserModel
from ..models.group import GroupModel
from ..logs import logger
from ..utils.exceptions import InvalidFolderStructure
from ..utils.exceptions import DoesNotExist
from ..utils import Compare
from ..events import MYDATA_EVENTS
from ..events import PostEvent
from ..events.stop import CheckIfShouldAbort
from ..threads.locks import LOCKS
from .dataview import MyDataDataViewModel
from .dataview import DATAVIEW_MODELS


class FoldersModel(MyDataDataViewModel):
    """
    Represents the Folders tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-many-public-methods
    # pylint: disable=arguments-differ
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def __init__(self):
        super(FoldersModel, self).__init__()

        self.columnNames = ["Id", "Folder (dataset)", "Location", "Created",
                            "Experiment", "Status", "Owner", "Group"]
        self.columnKeys = ["dataViewId", "folderName", "location", "created",
                           "experimentTitle", "status",
                           "owner.username", "group.shortName"]

        if sys.platform.startswith("win"):
            self.defaultColumnWidths = [40, 185, 200, 80, 150, 160, 90, 150]
        else:
            self.defaultColumnWidths = [40, 185, 200, 80, 160, 160, 90, 150]

        self.filterFields = \
            ["folderName", "location", "owner.username", "experimentTitle"]

        # When processing cached datafile lookups, attempting to update the
        # status field for every cache lookup would result in too many GUI
        # update events, so we avoid requesting folders view updates for every
        # datafile lookup, and instead use a timer.  "self.foldersToUpdate"
        # keeps track of which folder rows need to be refreshed for each timer
        # event:
        self.foldersToUpdate = collections.deque()

    def GetFolderRecord(self, row):
        """
        Return the folder model at a given row number (starting with row 0).
        """
        return self.rowsData[row]

    def GetValueByRow(self, row, col):
        """
        This method is called to provide the rowsData object for a
        particular row,col
        """
        # Workaround for a thread synchronization issue:
        try:
            assert self.rowsData[row]
        except IndexError:
            return ""
        columnKey = self.GetColumnKeyName(col)
        if columnKey.startswith("owner."):
            ownerKey = columnKey.split("owner.")[1]
            owner = self.rowsData[row].owner
            return owner.GetValueForKey(ownerKey) if owner else ""
        elif columnKey.startswith("group."):
            groupKey = columnKey.split("group.")[1]
            group = self.rowsData[row].group
            return group.GetValueForKey(groupKey) if group else ""
        return str(self.rowsData[row].GetValueForKey(columnKey))

    def GetFolderPath(self, row):
        """
        Get folder path.
        """
        return os.path.join(
            self.rowsData[row].location, self.rowsData[row].folderName)

    def GetAttrByRow(self, row, col, attr):
        """
        Called to check if non-standard attributes
        should be used in the cell at (row, col)
        """
        # pylint: disable=unused-argument
        # pylint: disable=no-self-use
        if col == 4:
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False

    def Compare(self, folderRecord1, folderRecord2, col, ascending):
        """
        This is called to assist with sorting the data in the view.  The
        first two args are instances of the DataViewItem class, so we
        need to convert them to row numbers with the GetRow method.
        Then it's just a matter of fetching the right values from our
        data set and comparing them.  The return value is -1, 0, or 1,
        just like Python 2's cmp() function.
        """
        try:
            folderRecord1 = self.rowsData[self.GetRow(folderRecord1)]
            folderRecord2 = self.rowsData[self.GetRow(folderRecord2)]
        except TypeError:
            # Compare is also called by Filter in which case we
            # don't need to convert from DataViewItem to FolderModel.
            pass
        if not ascending:
            folderRecord2, folderRecord1 = folderRecord1, folderRecord2
        if col == 0 or col == 3:
            obj1 = int(folderRecord1.dataViewId)
            obj2 = int(folderRecord2.dataViewId)
        else:
            obj1 = folderRecord1.GetValueForKey(self.columnKeys[col])
            obj2 = folderRecord2.GetValueForKey(self.columnKeys[col])
        return Compare(obj1, obj2)

    def AddRow(self, folderModel):
        """
        Add folder model to folders model and notify view.
        """
        if CheckIfShouldAbort():
            return
        super(FoldersModel, self).AddRow(folderModel)

        startDataUploadsForFolderEvent = \
            MYDATA_EVENTS.StartUploadsForFolderEvent(
                folderModel=folderModel)
        PostEvent(startDataUploadsForFolderEvent)

    def FolderStatusUpdated(self, folderModel, delay=False):
        """
        Ensure that updated folder status is reflected in the view.
        """
        if delay:
            if folderModel not in self.foldersToUpdate:
                with LOCKS.foldersToUpdate:
                    self.foldersToUpdate.append(folderModel)
        for row in range(0, self.GetCount()):
            if self.rowsData[row] == folderModel:
                col = self.columnNames.index("Status")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)

    def ScanFolders(self, writeProgressUpdateToStatusBar):
        """
        Scan dataset folders.
        """
        usersModel = DATAVIEW_MODELS['users']
        groupsModel = DATAVIEW_MODELS['groups']
        if self.GetCount() > 0:
            self.DeleteAllRows()
            self.foldersToUpdate.clear()
        if usersModel.GetCount() > 0:
            usersModel.DeleteAllRows()
        if groupsModel.GetCount() > 0:
            groupsModel.DeleteAllRows()
        dataDir = SETTINGS.general.dataDirectory
        defaultOwner = SETTINGS.general.defaultOwner
        folderStructure = SETTINGS.advanced.folderStructure
        logger.debug("FoldersModel.ScanFolders(): Scanning " + dataDir + "...")
        if folderStructure.startswith("Username") or \
                folderStructure.startswith("Email"):
            self.ScanForUserFolders(writeProgressUpdateToStatusBar)
        elif folderStructure.startswith("User Group"):
            self.ScanForGroupFolders(writeProgressUpdateToStatusBar)
        elif folderStructure.startswith("Experiment"):
            self.ScanForExperimentFolders(dataDir, defaultOwner,
                                          defaultOwner.username)
        elif folderStructure.startswith("Dataset"):
            self.ScanForDatasetFolders(dataDir, defaultOwner,
                                       defaultOwner.username)
        else:
            raise InvalidFolderStructure("Unknown folder structure.")

    def ScanForUserFolders(self, writeProgressUpdateToStatusBar):
        """
        Scan for user folders.
        """
        usersModel = DATAVIEW_MODELS['users']
        dataDir = SETTINGS.general.dataDirectory
        userOrGroupFilterString = '*%s*' % SETTINGS.filters.userFilter
        folderStructure = SETTINGS.advanced.folderStructure
        uploadInvalidUserOrGroupFolders = \
            SETTINGS.advanced.uploadInvalidUserOrGroupFolders
        filesDepth1 = glob(os.path.join(dataDir, userOrGroupFilterString))
        dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
        userFolderNames = [os.path.basename(d) for d in dirsDepth1]
        numUserFoldersScanned = 0
        for userFolderName in userFolderNames:
            if CheckIfShouldAbort():
                return
            if folderStructure.startswith("Username"):
                logger.debug("Found folder assumed to be username: " +
                             userFolderName)
            elif folderStructure.startswith("Email"):
                logger.debug("Found folder assumed to be email: " +
                             userFolderName)
            try:
                if folderStructure.startswith("Username"):
                    userRecord = UserModel.GetUserByUsername(userFolderName)
                elif folderStructure.startswith("Email"):
                    userRecord = UserModel.GetUserByEmail(userFolderName)
                else:
                    userRecord = None
            except DoesNotExist:
                userRecord = None
            if CheckIfShouldAbort():
                return
            usersDataViewId = usersModel.GetMaxDataViewId() + 1
            if not userRecord:
                message = "Didn't find a MyTardis user record for folder " \
                    "\"%s\" in %s" % (userFolderName, dataDir)
                logger.warning(message)
                if not uploadInvalidUserOrGroupFolders:
                    logger.warning("Skipping %s, because "
                                   "'Upload invalid user folders' "
                                   "setting is not checked." % userFolderName)
                    continue
                if folderStructure.startswith("Username"):
                    userRecord = UserModel(
                        username=userFolderName, userNotFoundInMyTardis=True)
                elif folderStructure.startswith("Email"):
                    userRecord = UserModel(
                        email=userFolderName, userNotFoundInMyTardis=True)
            userRecord.dataViewId = usersDataViewId
            usersModel.AddRow(userRecord)

            userFolderPath = os.path.join(dataDir, userFolderName)
            logger.debug("Folder structure: " + folderStructure)
            if folderStructure == 'Username / Dataset' or \
                    folderStructure == 'Email / Dataset':
                self.ScanForDatasetFolders(userFolderPath, userRecord,
                                           userFolderName)
            elif folderStructure == \
                    'Username / Experiment / Dataset' or \
                    folderStructure == 'Email / Experiment / Dataset':
                self.ScanForExperimentFolders(userFolderPath, userRecord,
                                              userFolderName)
            elif folderStructure == \
                    'Username / "MyTardis" / Experiment / Dataset':
                userFolderContents = os.listdir(userFolderPath)
                myTardisFolderName = None
                for item in userFolderContents:
                    if item.lower() == 'mytardis':
                        myTardisFolderName = item
                if not myTardisFolderName:
                    message = 'Didn\'t find "MyTardis" folder in ' \
                        '"%s"' % userFolderPath
                    logger.warning(message)
                    continue
                myTardisFolderPath = os.path.join(userFolderPath,
                                                  myTardisFolderName)
                self.ScanForExperimentFolders(myTardisFolderPath,
                                              userRecord,
                                              userFolderName)
            if CheckIfShouldAbort():
                return

            numUserFoldersScanned += 1
            if threading.current_thread().name == "MainThread":
                writeProgressUpdateToStatusBar(numUserFoldersScanned)
            else:
                wx.CallAfter(
                    writeProgressUpdateToStatusBar, numUserFoldersScanned)

    def ScanForGroupFolders(self, writeProgressUpdateToStatusBar):
        """
        Scan for group folders.
        """
        groupsModel = DATAVIEW_MODELS['groups']
        dataDir = SETTINGS.general.dataDirectory
        userOrGroupFilterString = '*%s*' % SETTINGS.filters.userFilter
        filesDepth1 = glob(os.path.join(dataDir, userOrGroupFilterString))
        dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
        groupFolderNames = [os.path.basename(d) for d in dirsDepth1]
        folderStructure = SETTINGS.advanced.folderStructure
        uploadInvalidUserOrGroupFolders = \
            SETTINGS.advanced.uploadInvalidUserOrGroupFolders
        numGroupFoldersScanned = 0
        for groupFolderName in groupFolderNames:
            if CheckIfShouldAbort():
                return
            logger.debug("Found folder assumed to be user group name: " +
                         groupFolderName)
            groupsDataViewId = groupsModel.GetMaxDataViewId() + 1
            try:
                groupName = SETTINGS.advanced.groupPrefix + groupFolderName
                groupRecord = GroupModel.GetGroupByName(groupName)
            except DoesNotExist:
                groupRecord = None
                message = "Didn't find a MyTardis user group record for " \
                    "folder \"%s\" in %s" % (groupFolderName,
                                             dataDir)
                logger.warning(message)
                if not uploadInvalidUserOrGroupFolders:
                    logger.warning("Skipping %s, because "
                                   "'Upload invalid user group folders' "
                                   "setting is not checked." % groupFolderName)
                    continue
            if CheckIfShouldAbort():
                return
            if groupRecord:
                groupRecord.dataViewId = groupsDataViewId
                groupsModel.AddRow(groupRecord)
            groupFolderPath = os.path.join(dataDir, groupFolderName)
            if folderStructure == \
                    'User Group / Instrument / Full Name / Dataset':
                self.ImportGroupFolders(groupFolderPath, groupRecord)
            elif folderStructure == 'User Group / Experiment / Dataset':
                defaultOwner = SETTINGS.general.defaultOwner
                self.ScanForExperimentFolders(groupFolderPath,
                                              owner=defaultOwner,
                                              groupRecord=groupRecord,
                                              groupFolderName=groupFolderName)
            else:
                raise InvalidFolderStructure("Unknown folder structure.")
            if CheckIfShouldAbort():
                return
            numGroupFoldersScanned += 1
            if threading.current_thread().name == "MainThread":
                writeProgressUpdateToStatusBar(numGroupFoldersScanned)
            else:
                wx.CallAfter(
                    writeProgressUpdateToStatusBar, numGroupFoldersScanned)

    def ScanForDatasetFolders(self, pathToScan, owner, userFolderName):
        """
        Scan for dataset folders.
        """
        try:
            logger.debug("Scanning " + pathToScan +
                         " for dataset folders...")
            datasetFilterString = '*%s*' % SETTINGS.filters.datasetFilter
            filesDepth1 = glob(os.path.join(pathToScan, datasetFilterString))
            dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
            dirsDepth1.sort(key=os.path.getmtime)
            datasetFolders = [os.path.basename(d) for d in dirsDepth1]
            for datasetFolderName in datasetFolders:
                logger.debug("Found folder assumed to be dataset: " +
                             datasetFolderName)
                if SETTINGS.filters.ignoreOldDatasets and \
                        DatasetIsTooOld(pathToScan, datasetFolderName):
                    continue
                if SETTINGS.filters.ignoreNewDatasets and \
                        DatasetIsTooNew(pathToScan, datasetFolderName):
                    continue
                dataViewId = self.GetMaxDataViewId() + 1
                folderModel = \
                    FolderModel(dataViewId=dataViewId,
                                folderName=datasetFolderName,
                                location=pathToScan,
                                userFolderName=userFolderName,
                                groupFolderName=None,
                                owner=owner)
                if CheckIfShouldAbort():
                    return
                folderModel.SetCreatedDate()
                if not owner.userNotFoundInMyTardis:
                    if owner.fullName.strip() != "":
                        experimentTitle = "%s - %s" \
                            % (SETTINGS.general.instrumentName, owner.fullName)
                    else:
                        experimentTitle = "%s - %s" \
                            % (SETTINGS.general.instrumentName, owner.username)
                elif owner.fullName != UserModel.userNotFoundString:
                    experimentTitle = "%s - %s (%s)" \
                        % (SETTINGS.general.instrumentName,
                           owner.fullName, UserModel.userNotFoundString)
                elif owner.username != UserModel.userNotFoundString:
                    experimentTitle = "%s - %s (%s)" \
                        % (SETTINGS.general.instrumentName, owner.username,
                           UserModel.userNotFoundString)
                elif owner.email != UserModel.userNotFoundString:
                    experimentTitle = "%s - %s (%s)" \
                        % (SETTINGS.general.instrumentName, owner.email,
                           UserModel.userNotFoundString)
                else:
                    experimentTitle = "%s - %s" \
                        % (SETTINGS.general.instrumentName,
                           UserModel.userNotFoundString)
                folderModel.experimentTitle = experimentTitle
                self.AddRow(folderModel)
        except:
            logger.error(traceback.format_exc())

    def ScanForExperimentFolders(self, pathToScan, owner, userFolderName=None,
                                 groupRecord=None, groupFolderName=None):
        """
        Scans for experiment folders.

        The MyTardis role account specified in the Settings dialog will
        automatically be given access (and ownership) to every experiment
        created.  If the experiment folder is found within a user folder,
        then that user will be given access, and similarly, if it is
        found within a user group folder, then the user group will be
        given access.
        """
        datasetFilterString = '*%s*' % SETTINGS.filters.datasetFilter
        expFilterString = '*%s*' % SETTINGS.filters.experimentFilter
        globDepth1 = glob(os.path.join(pathToScan, expFilterString))
        dirsDepth1 = [item for item in globDepth1 if os.path.isdir(item)]
        expFolders = [os.path.basename(d) for d in dirsDepth1]
        folderStructure = SETTINGS.advanced.folderStructure
        for expFolderName in expFolders:
            expFolderPath = os.path.join(pathToScan, expFolderName)
            globDepth1 = glob(os.path.join(expFolderPath, datasetFilterString))
            filesDepth1 = [item for item in globDepth1 if os.path.isfile(item)]
            dirsDepth1 = [item for item in globDepth1 if os.path.isdir(item)]
            datasetFolders = [os.path.basename(d) for d in dirsDepth1]
            for datasetFolderName in datasetFolders:
                if SETTINGS.filters.ignoreOldDatasets and \
                        DatasetIsTooOld(expFolderPath, datasetFolderName):
                    continue
                if SETTINGS.filters.ignoreNewDatasets and \
                        DatasetIsTooNew(expFolderPath, datasetFolderName):
                    continue
                dataViewId = self.GetMaxDataViewId() + 1
                folderModel = \
                    FolderModel(dataViewId=dataViewId,
                                folderName=datasetFolderName,
                                location=expFolderPath,
                                userFolderName=userFolderName,
                                groupFolderName=groupFolderName,
                                owner=owner)
                if CheckIfShouldAbort():
                    return
                if folderStructure.startswith("Username") or \
                        folderStructure.startswith("Email") or \
                        folderStructure.startswith("Experiment"):
                    folderModel.experimentTitle = expFolderName
                elif folderStructure.startswith("User Group"):
                    folderModel.group = groupRecord
                    if groupRecord:
                        groupName = groupRecord.shortName
                    else:
                        groupName = groupFolderName
                    folderModel.experimentTitle = \
                        "%s - %s" % (groupName, expFolderName)
                else:
                    raise InvalidFolderStructure("Unknown folder structure.")
                folderModel.SetCreatedDate()
                self.AddRow(folderModel)
            if filesDepth1:
                logger.info("Found %s experiment file(s) in %s\n"
                            % (len(filesDepth1), expFolderPath))
                dataViewId = self.GetMaxDataViewId() + 1
                folderModel = \
                    FolderModel(dataViewId=dataViewId,
                                folderName="__EXPERIMENT_FILES__",
                                location=expFolderPath,
                                userFolderName=userFolderName,
                                groupFolderName=groupFolderName,
                                owner=owner,
                                isExperimentFilesFolder=True)
                if CheckIfShouldAbort():
                    return
                folderModel.experimentTitle = expFolderName
                folderModel.SetCreatedDate()
                self.AddRow(folderModel)

    def ImportGroupFolders(self, groupFolderPath, groupModel):
        """
        Imports folders structured according to the
        "User Group / Instrument / Researcher's Name / Dataset"
        folder structure, starting with user group folders,
        e.g. D:\\Data\\Smith-Lab\\

        Rather than reading data from any folder we happen to find at
        the Instrument level, MyData uses the instrument name specified
        in MyData's Settings dialog.  That way, MyData can be run on a
        collection of data from multiple instruments, and just select
        one instrument at a time.

        For the User Group / Instrument / Researcher's Name / Dataset
        folder structure, the default owner in MyTardis will always
        by the user listed in MyData's settings dialog.  An additional
        ObjectACL will be created in MyTardis to grant access to the
        User Group.  The researcher's name in this folder structure is
        used to determine the default experiment name, but it is not
        used to determine access control.
        """
        try:
            logger.debug("Scanning " + groupFolderPath +
                         " for instrument folders...")
            datasetFilterString = '*%s*' % SETTINGS.filters.datasetFilter
            instrumentName = SETTINGS.general.instrumentName
            filesDepth1 = glob(os.path.join(groupFolderPath, instrumentName))
            dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
            instrumentFolders = [os.path.basename(d) for d in dirsDepth1]

            if len(instrumentFolders) > 1:
                message = "Multiple instrument folders found in %s" \
                    % groupFolderPath
                logger.warning(message)
            elif not instrumentFolders:
                message = "No instrument folder was found in %s" \
                    % groupFolderPath
                logger.warning(message)
                return

            instrumentFolderPath = \
                os.path.join(groupFolderPath, SETTINGS.general.instrumentName)

            if not os.path.exists(instrumentFolderPath):
                logger.warning("Path %s doesn't exist." % instrumentFolderPath)
                return

            owner = SETTINGS.general.defaultOwner

            logger.debug("Scanning " + instrumentFolderPath +
                         " for user folders...")
            userFolders = os.walk(instrumentFolderPath).next()[1]
            if CheckIfShouldAbort():
                return
            for userFolderName in userFolders:
                userFolderPath = os.path.join(instrumentFolderPath,
                                              userFolderName)
                logger.debug("Scanning " + userFolderPath +
                             " for dataset folders...")
                filesDepth1 = glob(os.path.join(userFolderPath,
                                                datasetFilterString))
                dirsDepth1 = [item for item in filesDepth1
                              if os.path.isdir(item)]
                datasetFolders = [os.path.basename(d) for d in dirsDepth1]
                for datasetFolderName in datasetFolders:
                    if SETTINGS.filters.ignoreOldDatasets and \
                            DatasetIsTooOld(userFolderPath, datasetFolderName):
                        continue
                    if SETTINGS.filters.ignoreNewDatasets and \
                            DatasetIsTooNew(userFolderPath, datasetFolderName):
                        continue
                    groupFolderName = os.path.basename(groupFolderPath)
                    dataViewId = self.GetMaxDataViewId() + 1
                    folderModel = \
                        FolderModel(dataViewId=dataViewId,
                                    folderName=datasetFolderName,
                                    location=userFolderPath,
                                    userFolderName=userFolderName,
                                    groupFolderName=groupFolderName,
                                    owner=owner)
                    if CheckIfShouldAbort():
                        return
                    folderModel.group = groupModel
                    folderModel.SetCreatedDate()
                    folderModel.experimentTitle = \
                        "%s - %s" % (SETTINGS.general.instrumentName,
                                     userFolderName)
                    self.AddRow(folderModel)
        except InvalidFolderStructure:
            raise
        except:
            logger.error(traceback.format_exc())

    def GetTotalNumFiles(self):
        """
        Get total number of files.
        """
        total = 0
        for folderModel in self.rowsData:
            total += folderModel.GetNumFiles()
        return total

    def ResetCounts(self):
        """
        Reset counts of uploaded files etc.
        """
        for folderModel in self.rowsData:
            folderModel.ResetCounts()


def DatasetIsTooOld(pathToScan, datasetFolderName):
    """
    If the supplied dataset folder is too old, according to
    our filtering settings, return True and log a warning
    """
    datasetFolderPath = os.path.join(pathToScan, datasetFolderName)
    ctimestamp = os.path.getctime(datasetFolderPath)
    ctime = datetime.fromtimestamp(ctimestamp)
    age = datetime.now() - ctime
    if age.total_seconds() > \
            SETTINGS.filters.ignoreOldDatasetIntervalSeconds:
        message = "Ignoring \"%s\", because it is " \
            "older than %d %s" \
            % (datasetFolderPath,
               SETTINGS.filters.ignoreIntervalNumber,
               SETTINGS.filters.ignoreIntervalUnit)
        logger.warning(message)
        return True
    return False


def DatasetIsTooNew(pathToScan, datasetFolderName):
    """
    If the supplied dataset folder is too new, according to
    our filtering settings, return True and log a warning
    """
    datasetFolderPath = os.path.join(pathToScan, datasetFolderName)
    ctimestamp = os.path.getctime(datasetFolderPath)
    ctime = datetime.fromtimestamp(ctimestamp)
    age = datetime.now() - ctime
    if age.total_seconds() < \
            SETTINGS.filters.ignoreNewDatasetIntervalSeconds:
        message = "Ignoring \"%s\", because it is " \
            "newer than %d %s" \
            % (datasetFolderPath,
               SETTINGS.filters.ignoreNewDatasetIntervalNumber,
               SETTINGS.filters.ignoreNewDatasetIntervalUnit)
        logger.warning(message)
        return True
    return False

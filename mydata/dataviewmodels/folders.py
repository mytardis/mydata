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
from ..events.stop import RaiseExceptionIfUserAborted
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
        RaiseExceptionIfUserAborted()
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
        if self.GetCount() > 0:
            self.DeleteAllRows()
            self.foldersToUpdate.clear()
        if DATAVIEW_MODELS['users'].GetCount() > 0:
            DATAVIEW_MODELS['users'].DeleteAllRows()
        if DATAVIEW_MODELS['groups'].GetCount() > 0:
            DATAVIEW_MODELS['groups'].DeleteAllRows()
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
        folderStructure = SETTINGS.advanced.folderStructure
        uploadInvalidUserOrGroupFolders = \
            SETTINGS.advanced.uploadInvalidUserOrGroupFolders
        numUserFoldersScanned = 0
        for userFolderName in \
                UserFolderNames(SETTINGS.general.dataDirectory):
            RaiseExceptionIfUserAborted()
            logger.debug(
                "Found folder assumed to be %s: %s" % (UserFolderType(),
                                                       userFolderName))
            try:
                userRecord = UserModel.GetUserForFolder(userFolderName)
            except DoesNotExist:
                userRecord = None
            RaiseExceptionIfUserAborted()
            usersDataViewId = DATAVIEW_MODELS['users'].GetMaxDataViewId() + 1
            if not userRecord:
                message = "Didn't find a MyTardis user record for folder " \
                    "\"%s\" in %s" % (userFolderName,
                                      SETTINGS.general.dataDirectory)
                logger.warning(message)
                if not uploadInvalidUserOrGroupFolders:
                    logger.warning("Skipping %s, because "
                                   "'Upload invalid user folders' "
                                   "setting is not checked." % userFolderName)
                    continue
                userRecord = UserModel.GetUserForFolder(
                    userFolderName, userNotFoundInMyTardis=True)
            userRecord.dataViewId = usersDataViewId
            DATAVIEW_MODELS['users'].AddRow(userRecord)

            userFolderPath = os.path.join(
                SETTINGS.general.dataDirectory, userFolderName)
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
            RaiseExceptionIfUserAborted()

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
        folderStructure = SETTINGS.advanced.folderStructure
        uploadInvalidUserOrGroupFolders = \
            SETTINGS.advanced.uploadInvalidUserOrGroupFolders
        numGroupFoldersScanned = 0
        for groupFolderName in \
                GroupFolderNames(SETTINGS.general.dataDirectory):
            RaiseExceptionIfUserAborted()
            logger.debug("Found folder assumed to be user group name: " +
                         groupFolderName)
            groupsDataViewId = DATAVIEW_MODELS['groups'].GetMaxDataViewId() + 1
            try:
                groupName = SETTINGS.advanced.groupPrefix + groupFolderName
                groupRecord = GroupModel.GetGroupByName(groupName)
            except DoesNotExist:
                groupRecord = None
                message = "Didn't find a MyTardis user group record for " \
                    "folder \"%s\" in %s" % (groupFolderName,
                                             SETTINGS.general.dataDirectory)
                logger.warning(message)
                if not uploadInvalidUserOrGroupFolders:
                    logger.warning("Skipping %s, because "
                                   "'Upload invalid user group folders' "
                                   "setting is not checked." % groupFolderName)
                    continue
            RaiseExceptionIfUserAborted()
            if groupRecord:
                groupRecord.dataViewId = groupsDataViewId
                DATAVIEW_MODELS['groups'].AddRow(groupRecord)
            groupFolderPath = os.path.join(
                SETTINGS.general.dataDirectory, groupFolderName)
            defaultOwner = SETTINGS.general.defaultOwner
            if folderStructure == \
                    'User Group / Instrument / Full Name / Dataset':
                self.ImportGroupFolders(groupFolderPath, groupRecord)
            elif folderStructure == 'User Group / Experiment / Dataset':
                self.ScanForExperimentFolders(groupFolderPath,
                                              owner=defaultOwner,
                                              groupRecord=groupRecord,
                                              groupFolderName=groupFolderName)
            elif folderStructure == 'User Group / Dataset':
                self.ScanForDatasetFolders(groupFolderPath,
                                           owner=defaultOwner,
                                           groupRecord=groupRecord,
                                           groupFolderName=groupFolderName)
            else:
                raise InvalidFolderStructure("Unknown folder structure.")
            RaiseExceptionIfUserAborted()
            numGroupFoldersScanned += 1
            if threading.current_thread().name == "MainThread":
                writeProgressUpdateToStatusBar(numGroupFoldersScanned)
            else:
                wx.CallAfter(
                    writeProgressUpdateToStatusBar, numGroupFoldersScanned)

    def ScanForDatasetFolders(self, pathToScan, owner, userFolderName=None,
                              groupRecord=None, groupFolderName=None):
        """
        Scan for dataset folders.
        """
        try:
            logger.debug("Scanning " + pathToScan + " for dataset folders...")
            for datasetFolderName in DatasetFolderNames(pathToScan):
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
                                groupFolderName=groupFolderName,
                                owner=owner,
                                group=groupRecord)
                RaiseExceptionIfUserAborted()
                folderModel.SetCreatedDate()
                SetExperimentTitle(folderModel, owner, groupFolderName)
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
        folderStructure = SETTINGS.advanced.folderStructure
        for expFolderName in ExperimentFolderNames(pathToScan):
            expFolderPath = os.path.join(pathToScan, expFolderName)
            for datasetFolderName in DatasetFolderNames(expFolderPath):
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
                                owner=owner,
                                group=groupRecord)
                RaiseExceptionIfUserAborted()
                if folderStructure.startswith("Username") or \
                        folderStructure.startswith("Email") or \
                        folderStructure.startswith("Experiment"):
                    folderModel.experimentTitle = expFolderName
                elif folderStructure.startswith("User Group / Experiment"):
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
            filesDepth1 = FilesInTopLevel(expFolderPath)
            if filesDepth1:
                logger.info("Found %s experiment file(s) in %s\n"
                            % (len(filesDepth1), expFolderPath))
                folderModel = \
                    FolderModel(dataViewId=self.GetMaxDataViewId() + 1,
                                folderName="__EXPERIMENT_FILES__",
                                location=expFolderPath,
                                userFolderName=userFolderName,
                                groupFolderName=groupFolderName,
                                owner=owner,
                                group=groupRecord,
                                isExperimentFilesFolder=True)
                RaiseExceptionIfUserAborted()
                folderModel.experimentTitle = expFolderName
                folderModel.SetCreatedDate()
                self.AddRow(folderModel)

    def ImportGroupFolders(self, groupFolderPath, groupRecord):
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

            instrumentFolderPath = \
                os.path.join(groupFolderPath, SETTINGS.general.instrumentName)

            if not os.path.exists(instrumentFolderPath):
                logger.warning("Path %s doesn't exist." % instrumentFolderPath)
                return

            owner = SETTINGS.general.defaultOwner

            logger.debug("Scanning " + instrumentFolderPath +
                         " for user folders...")
            userFolders = os.walk(instrumentFolderPath).next()[1]
            RaiseExceptionIfUserAborted()
            for userFolderName in userFolders:
                userFolderPath = os.path.join(instrumentFolderPath,
                                              userFolderName)
                logger.debug("Scanning " + userFolderPath +
                             " for dataset folders...")
                for datasetFolderName in DatasetFolderNames(userFolderPath):
                    if SETTINGS.filters.ignoreOldDatasets and \
                            DatasetIsTooOld(userFolderPath, datasetFolderName):
                        continue
                    if SETTINGS.filters.ignoreNewDatasets and \
                            DatasetIsTooNew(userFolderPath, datasetFolderName):
                        continue
                    groupFolderName = os.path.basename(groupFolderPath)
                    folderModel = \
                        FolderModel(dataViewId=self.GetMaxDataViewId() + 1,
                                    folderName=datasetFolderName,
                                    location=userFolderPath,
                                    userFolderName=userFolderName,
                                    groupFolderName=groupFolderName,
                                    owner=owner,
                                    group=groupRecord)
                    RaiseExceptionIfUserAborted()
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
            total += folderModel.numFiles
        return total

    def ResetCounts(self):
        """
        Reset counts of uploaded files etc.
        """
        for folderModel in self.rowsData:
            folderModel.ResetCounts()


def FolderNames(pathToScan, filterPattern=''):
    """
    List of folder names in path matching the filter pattern
    (or all folders in the specified path if there is no filter).
    """
    filesDepth1 = glob(os.path.join(pathToScan, '*%s*' % filterPattern))
    dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
    return [os.path.basename(d) for d in dirsDepth1]


def UserFolderNames(pathToScan):
    """
    List of folder names in path matching user filter (or
    all folders in the specified path if there is no filter).
    """
    return FolderNames(pathToScan, SETTINGS.filters.userFilter)


def GroupFolderNames(pathToScan):
    """
    List of folder names in path matching group filter (or
    all folders in the specified path if there is no filter).

    The filter field for user groups is still stored as
    SETTING.filter.userFilter even though the user interface
    (settings dialog) presents it as a "user group" filter
    when a User Group folder structure is selected.
    """
    return FolderNames(pathToScan, SETTINGS.filters.userFilter)


def DatasetFolderNames(pathToScan):
    """
    Return a list of dataset folder names in the specified
    folder path, matching the dataset filter (if one exists).
    """
    return FolderNames(pathToScan, SETTINGS.filters.datasetFilter)


def ExperimentFolderNames(pathToScan):
    """
    Return a list of experiment folder names in the specified
    folder path, matching the experiment filter (if one exists).
    """
    return FolderNames(pathToScan, SETTINGS.filters.experimentFilter)


def FilesInTopLevel(expFolderPath):
    """
    Return a list of file names in the specified experiment
    folder path, not within any specific dataset folder.
    """
    globDepth1 = glob(os.path.join(
        expFolderPath, '*%s*' % SETTINGS.filters.datasetFilter))
    return [item for item in globDepth1 if os.path.isfile(item)]


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


def UserFolderType():
    """
    Return username or email, depending on the folder structure
    """
    folderStructure = SETTINGS.advanced.folderStructure
    if folderStructure.startswith("Email"):
        return "email"
    return "username"


def SetExperimentTitle(folderModel, owner, groupFolderName):
    """
    Set the folderModel.experimentTitle for cases where
    the user hasn't explicitly specified it in a folder name
    """
    folderStructure = SETTINGS.advanced.folderStructure
    if folderStructure.startswith("User Group / Experiment"):
        experimentTitle = "%s - %s" \
            % (SETTINGS.general.instrumentName, groupFolderName)
    elif folderStructure.startswith("User Group / Dataset"):
        experimentTitle = groupFolderName
    elif not owner.userNotFoundInMyTardis:
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

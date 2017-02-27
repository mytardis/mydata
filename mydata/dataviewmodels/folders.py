"""
Represents the Folders tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import threading
import os
import sys
import traceback
from datetime import datetime
from glob import glob

import wx

from ..models.folder import FolderModel
from ..models.user import UserModel
from ..models.group import GroupModel
from ..logs import logger
from ..utils.exceptions import InvalidFolderStructure
from ..utils.exceptions import DoesNotExist
from ..utils import EndBusyCursorIfRequired
from ..utils import Compare
from ..events import MYDATA_EVENTS
from ..events import PostEvent
from .dataview import MyDataDataViewModel


class FoldersModel(MyDataDataViewModel):
    """
    Represents the Folders tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
    # pylint: disable=arguments-differ
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def __init__(self, usersModel, groupsModel, settingsModel):
        super(FoldersModel, self).__init__()

        self.usersModel = usersModel
        self.groupsModel = groupsModel
        self.settingsModel = settingsModel

        self.columnNames = ["Id", "Folder (dataset)", "Location", "Created",
                            "Experiment", "Status", "Owner", "Group"]
        self.columnKeys = ["dataViewId", "folder", "location", "created",
                           "experimentTitle", "status",
                           "owner.username", "group.shortName"]

        if sys.platform.startswith("win"):
            self.defaultColumnWidths = [40, 185, 200, 80, 150, 160, 90, 150]
        else:
            self.defaultColumnWidths = [40, 185, 200, 80, 160, 160, 90, 150]

        self.ignoreIntervalSeconds = 0
        self.ignoreOldDatasets = False
        self.ignoreIntervalNumber = 0
        self.ignoreIntervalUnit = "months"

    def GetFolderRecord(self, row):
        """
        Return the folder model at a given row number (starting with row 0).
        """
        return self.rowsData[row]

    def Filter(self, searchString):
        """
        Only show folders matching the query string, typed in the search box
        in the upper-right corner of the main window.
        """
        self.searchString = searchString
        query = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.unfilteredData = list(self.rowsData)

        for row in reversed(range(0, self.GetRowCount())):
            folderModel = self.rowsData[row]
            if query not in folderModel.folder.lower() and \
                    query not in folderModel.location.lower() and \
                    query not in folderModel.owner.GetUsername().lower() and \
                    query not in folderModel.experimentTitle:
                self.filteredData.append(folderModel)
                del self.rowsData[row]
                # Notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            folderModel = self.filteredData[filteredRow]
            if query in folderModel.folder.lower() or \
                    query in folderModel.location.lower() or \
                    query in folderModel.owner.GetUsername().lower() or \
                    query in folderModel.experimentTitle:
                # Model doesn't care about currently sorted column.
                # Always use ID.
                row = 0
                col = 0
                ascending = True  # Need to get current sort direction
                while row < self.GetRowCount() and \
                        self.Compare(self.rowsData[row],
                                     self.filteredData[filteredRow],
                                     col, ascending) < 0:
                    row += 1

                if row == self.GetRowCount():
                    self.rowsData\
                        .append(self.filteredData[filteredRow])
                    # Notify the view(s) using this model
                    # that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowAppended()
                    else:
                        wx.CallAfter(self.RowAppended)
                else:
                    self.rowsData.insert(
                        row, self.filteredData[filteredRow])
                    # Notify the view(s) using this model
                    # that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowInserted(row)
                    else:
                        wx.CallAfter(self.RowInserted)
                del self.filteredData[filteredRow]
                if self.GetFilteredRowCount() == 0:
                    self.filtered = False

    def GetValueByRow(self, row, col):
        """
        This method is called to provide the rowsData object for a
        particular row,col
        """
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
            self.rowsData[row].location, self.rowsData[row].folder)

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
            return Compare(int(folderRecord1.dataViewId),
                           int(folderRecord2.dataViewId))
        else:
            return Compare(folderRecord1.GetValueForKey(self.columnKeys[col]),
                           folderRecord2.GetValueForKey(self.columnKeys[col]))

    def AddRow(self, folderModel):
        """
        Add folder model to folders model and notify view.
        """
        super(FoldersModel, self).AddRow(folderModel)

        startDataUploadsForFolderEvent = \
            MYDATA_EVENTS.StartUploadsForFolderEvent(
                folderModel=folderModel)
        PostEvent(startDataUploadsForFolderEvent)

    def FolderStatusUpdated(self, folderModel):
        """
        Ensure that updated folder status is reflected in the view.
        """
        for row in range(0, self.GetCount()):
            if self.rowsData[row] == folderModel:
                col = self.columnNames.index("Status")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)

    def ScanFolders(self, writeProgressUpdateToStatusBar, shouldAbort):
        """
        Scan dataset folders.
        """
        if self.GetCount() > 0:
            self.DeleteAllRows()
        if self.usersModel.GetCount() > 0:
            self.usersModel.DeleteAllRows()
        if self.groupsModel.GetCount() > 0:
            self.groupsModel.DeleteAllRows()
        dataDir = self.settingsModel.general.dataDirectory
        defaultOwner = self.settingsModel.defaultOwner
        folderStructure = self.settingsModel.advanced.folderStructure
        self.ignoreOldDatasets = self.settingsModel.filters.ignoreOldDatasets
        if self.ignoreOldDatasets:
            seconds = dict(day=24 * 60 * 60)
            seconds['year'] = int(365.25 * seconds['day'])
            seconds['month'] = seconds['year'] / 12
            singularIgnoreIntervalUnit = \
                self.settingsModel.filters.ignoreOldDatasetIntervalUnit\
                .rstrip('s')
            ignoreIntervalUnitSeconds = seconds[singularIgnoreIntervalUnit]

            self.ignoreIntervalNumber = \
                self.settingsModel.filters.ignoreOldDatasetIntervalNumber
            self.ignoreIntervalUnit = \
                self.settingsModel.filters.ignoreOldDatasetIntervalUnit
            self.ignoreIntervalSeconds = \
                self.ignoreIntervalNumber * ignoreIntervalUnitSeconds
        logger.debug("FoldersModel.ScanFolders(): Scanning " + dataDir + "...")
        if folderStructure.startswith("Username") or \
                folderStructure.startswith("Email"):
            self.ScanForUserFolders(writeProgressUpdateToStatusBar,
                                    shouldAbort)
        elif folderStructure.startswith("User Group"):
            self.ScanForGroupFolders(writeProgressUpdateToStatusBar,
                                     shouldAbort)
        elif folderStructure.startswith("Experiment"):
            self.ScanForExperimentFolders(dataDir, defaultOwner,
                                          defaultOwner.GetUsername())
        elif folderStructure.startswith("Dataset"):
            self.ScanForDatasetFolders(dataDir, defaultOwner,
                                       defaultOwner.GetUsername())
        else:
            raise InvalidFolderStructure("Unknown folder structure.")

    def ScanForUserFolders(self, writeProgressUpdateToStatusBar, shouldAbort):
        """
        Scan for user folders.
        """
        dataDir = self.settingsModel.general.dataDirectory
        userOrGroupFilterString = \
            '*%s*' % self.settingsModel.filters.userFilter
        folderStructure = self.settingsModel.advanced.folderStructure
        uploadInvalidUserOrGroupFolders = \
            self.settingsModel.advanced.uploadInvalidUserOrGroupFolders
        filesDepth1 = glob(os.path.join(dataDir, userOrGroupFilterString))
        dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
        userFolderNames = [os.path.basename(d) for d in dirsDepth1]
        for userFolderName in userFolderNames:
            if shouldAbort():
                wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage,
                             "Data scans and uploads were canceled.")
                wx.CallAfter(EndBusyCursorIfRequired)
                return
            if folderStructure.startswith("Username"):
                logger.debug("Found folder assumed to be username: " +
                             userFolderName)
            elif folderStructure.startswith("Email"):
                logger.debug("Found folder assumed to be email: " +
                             userFolderName)
            try:
                if folderStructure.startswith("Username"):
                    userRecord = \
                        UserModel.GetUserByUsername(self.settingsModel,
                                                    userFolderName)
                elif folderStructure.startswith("Email"):
                    userRecord = \
                        UserModel.GetUserByEmail(self.settingsModel,
                                                 userFolderName)
                else:
                    userRecord = None
            except DoesNotExist:
                userRecord = None
            if shouldAbort():
                wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage,
                             "Data scans and uploads were canceled.")
                wx.CallAfter(EndBusyCursorIfRequired)
                return
            usersDataViewId = self.usersModel.GetMaxDataViewId() + 1
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
                    userRecord = UserModel(settingsModel=self.settingsModel,
                                           username=userFolderName,
                                           userNotFoundInMyTardis=True)
                elif folderStructure.startswith("Email"):
                    userRecord = \
                        UserModel(settingsModel=self.settingsModel,
                                  email=userFolderName,
                                  userNotFoundInMyTardis=True)
            userRecord.dataViewId = usersDataViewId
            self.usersModel.AddRow(userRecord)

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
                    logger.error(message)
                    raise InvalidFolderStructure(message)
                myTardisFolderPath = os.path.join(userFolderPath,
                                                  myTardisFolderName)
                self.ScanForExperimentFolders(myTardisFolderPath,
                                              userRecord,
                                              userFolderName)
            if shouldAbort():
                wx.CallAfter(wx.GetApp().GetMainFrame()
                             .SetStatusMessage,
                             "Data scans and uploads were canceled.")
                wx.CallAfter(EndBusyCursorIfRequired)
                return

            if threading.current_thread().name == "MainThread":
                writeProgressUpdateToStatusBar()
            else:
                wx.CallAfter(writeProgressUpdateToStatusBar)

    def ScanForGroupFolders(self, writeProgressUpdateToStatusBar, shouldAbort):
        """
        Scan for group folders.
        """
        dataDir = self.settingsModel.general.dataDirectory
        userOrGroupFilterString = \
            '*%s*' % self.settingsModel.filters.userFilter
        filesDepth1 = glob(os.path.join(dataDir, userOrGroupFilterString))
        dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
        groupFolderNames = [os.path.basename(d) for d in dirsDepth1]
        folderStructure = self.settingsModel.advanced.folderStructure
        uploadInvalidUserOrGroupFolders = \
            self.settingsModel.advanced.uploadInvalidUserOrGroupFolders
        for groupFolderName in groupFolderNames:
            if shouldAbort():
                wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage,
                             "Data scans and uploads were canceled.")
                wx.CallAfter(EndBusyCursorIfRequired)
                return
            logger.debug("Found folder assumed to be user group name: " +
                         groupFolderName)
            groupsDataViewId = self.groupsModel.GetMaxDataViewId() + 1
            try:
                groupName = self.settingsModel.advanced.groupPrefix + \
                    groupFolderName
                groupRecord = \
                    GroupModel.GetGroupByName(self.settingsModel, groupName)
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
            if shouldAbort():
                wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage,
                             "Data scans and uploads were canceled.")
                wx.CallAfter(EndBusyCursorIfRequired)
                return
            if groupRecord:
                groupRecord.dataViewId = groupsDataViewId
                self.groupsModel.AddRow(groupRecord)
            groupFolderPath = os.path.join(dataDir, groupFolderName)
            if folderStructure == \
                    'User Group / Instrument / Full Name / Dataset':
                self.ImportGroupFolders(groupFolderPath, groupRecord)
            elif folderStructure == 'User Group / Experiment / Dataset':
                defaultOwner = self.settingsModel.defaultOwner
                self.ScanForExperimentFolders(groupFolderPath,
                                              owner=defaultOwner,
                                              groupRecord=groupRecord,
                                              groupFolderName=groupFolderName)
            else:
                raise InvalidFolderStructure("Unknown folder structure.")
            if shouldAbort():
                wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage,
                             "Data scans and uploads were canceled.")
                wx.CallAfter(EndBusyCursorIfRequired)
                return
            if threading.current_thread().name == "MainThread":
                writeProgressUpdateToStatusBar()
            else:
                wx.CallAfter(writeProgressUpdateToStatusBar)

    def ScanForDatasetFolders(self, pathToScan, owner, userFolderName):
        """
        Scan for dataset folders.
        """
        try:
            logger.debug("Scanning " + pathToScan +
                         " for dataset folders...")
            datasetFilterString = \
                '*%s*' % self.settingsModel.filters.datasetFilter
            filesDepth1 = glob(os.path.join(pathToScan, datasetFilterString))
            dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
            datasetFolders = [os.path.basename(d) for d in dirsDepth1]
            for datasetFolderName in datasetFolders:
                logger.debug("Found folder assumed to be dataset: " +
                             datasetFolderName)
                if self.ignoreOldDatasets:
                    datasetFolderPath = os.path.join(pathToScan,
                                                     datasetFolderName)
                    ctimestamp = os.path.getctime(datasetFolderPath)
                    ctime = datetime.fromtimestamp(ctimestamp)
                    age = datetime.now() - ctime
                    if age.total_seconds() > \
                            self.ignoreIntervalSeconds:
                        message = "Ignoring \"%s\", because it is " \
                            "older than %d %s" \
                            % (datasetFolderPath,
                               self.ignoreIntervalNumber,
                               self.ignoreIntervalUnit)
                        logger.warning(message)
                        continue
                dataViewId = self.GetMaxDataViewId() + 1
                folderModel = \
                    FolderModel(dataViewId=dataViewId,
                                folder=datasetFolderName,
                                location=pathToScan,
                                userFolderName=userFolderName,
                                groupFolderName=None,
                                owner=owner,
                                settingsModel=self.settingsModel)
                folderModel.SetCreatedDate()
                if not owner.userNotFoundInMyTardis:
                    if owner.GetName().strip() != "":
                        experimentTitle = "%s - %s" \
                            % (self.settingsModel.general.instrumentName,
                               owner.GetName())
                    else:
                        experimentTitle = "%s - %s" \
                            % (self.settingsModel.general.instrumentName,
                               owner.GetUsername())
                elif owner.GetName() != UserModel.userNotFoundString:
                    experimentTitle = "%s - %s (%s)" \
                        % (self.settingsModel.general.instrumentName,
                           owner.GetName(),
                           UserModel.userNotFoundString)
                elif owner.GetUsername() != UserModel.userNotFoundString:
                    experimentTitle = "%s - %s (%s)" \
                        % (self.settingsModel.general.instrumentName,
                           owner.GetUsername(),
                           UserModel.userNotFoundString)
                elif owner.GetEmail() != UserModel.userNotFoundString:
                    experimentTitle = "%s - %s (%s)" \
                        % (self.settingsModel.general.instrumentName,
                           owner.GetEmail(),
                           UserModel.userNotFoundString)
                else:
                    experimentTitle = "%s - %s" \
                        % (self.settingsModel.general.instrumentName,
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
        datasetFilterString = '*%s*' % self.settingsModel.filters.datasetFilter
        expFilterString = '*%s*' % self.settingsModel.filters.experimentFilter
        globDepth1 = glob(os.path.join(pathToScan, expFilterString))
        dirsDepth1 = [item for item in globDepth1 if os.path.isdir(item)]
        expFolders = [os.path.basename(d) for d in dirsDepth1]
        folderStructure = self.settingsModel.advanced.folderStructure
        for expFolderName in expFolders:
            expFolderPath = os.path.join(pathToScan, expFolderName)
            globDepth1 = glob(os.path.join(expFolderPath, datasetFilterString))
            filesDepth1 = [item for item in globDepth1 if os.path.isfile(item)]
            dirsDepth1 = [item for item in globDepth1 if os.path.isdir(item)]
            datasetFolders = [os.path.basename(d) for d in dirsDepth1]
            for datasetFolderName in datasetFolders:
                if self.ignoreOldDatasets:
                    datasetFolderPath = os.path.join(expFolderPath,
                                                     datasetFolderName)
                    ctimestamp = os.path.getctime(datasetFolderPath)
                    ctime = datetime.fromtimestamp(ctimestamp)
                    age = datetime.now() - ctime
                    if age.total_seconds() > self.ignoreIntervalSeconds:
                        message = "Ignoring \"%s\", because it is " \
                            "older than %d %s" \
                            % (datasetFolderPath, self.ignoreIntervalNumber,
                               self.ignoreIntervalUnit)
                        logger.warning(message)
                        continue
                dataViewId = self.GetMaxDataViewId() + 1
                folderModel = \
                    FolderModel(dataViewId=dataViewId,
                                folder=datasetFolderName,
                                location=expFolderPath,
                                userFolderName=userFolderName,
                                groupFolderName=groupFolderName,
                                owner=owner,
                                settingsModel=self.settingsModel)
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
            if len(filesDepth1) > 0:
                logger.info("Found %s experiment file(s) in %s\n"
                            % (len(filesDepth1), expFolderPath))
                dataViewId = self.GetMaxDataViewId() + 1
                folderModel = \
                    FolderModel(dataViewId=dataViewId,
                                folder="__EXPERIMENT_FILES__",
                                location=expFolderPath,
                                userFolderName=userFolderName,
                                groupFolderName=groupFolderName,
                                owner=owner,
                                settingsModel=self.settingsModel,
                                isExperimentFilesFolder=True)
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
            datasetFilterString = \
                '*%s*' % self.settingsModel.filters.datasetFilter
            instrumentName = self.settingsModel.general.instrumentName
            filesDepth1 = glob(os.path.join(groupFolderPath, instrumentName))
            dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
            instrumentFolders = [os.path.basename(d) for d in dirsDepth1]

            if len(instrumentFolders) > 1:
                message = "Multiple instrument folders found in %s" \
                    % groupFolderPath
                logger.warning(message)
            elif len(instrumentFolders) == 0:
                message = "No instrument folder was found in %s" \
                    % groupFolderPath
                logger.warning(message)
                return

            instrumentFolderPath = \
                os.path.join(groupFolderPath,
                             self.settingsModel.general.instrumentName)

            if not os.path.exists(instrumentFolderPath):
                logger.warning("Path %s doesn't exist." % instrumentFolderPath)
                return

            owner = self.settingsModel.defaultOwner

            logger.debug("Scanning " + instrumentFolderPath +
                         " for user folders...")
            userFolders = os.walk(instrumentFolderPath).next()[1]
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
                    if self.ignoreOldDatasets:
                        datasetFolderPath = os.path.join(userFolderPath,
                                                         datasetFolderName)
                        ctimestamp = os.path.getctime(datasetFolderPath)
                        ctime = datetime.fromtimestamp(ctimestamp)
                        age = datetime.now() - ctime
                        if age.total_seconds() > self.ignoreIntervalSeconds:
                            message = "Ignoring \"%s\", because it is " \
                                "older than %d %s" \
                                % (datasetFolderPath,
                                   self.ignoreIntervalNumber,
                                   self.ignoreIntervalUnit)
                            logger.warning(message)
                            continue
                    groupFolderName = os.path.basename(groupFolderPath)
                    dataViewId = self.GetMaxDataViewId() + 1
                    folderModel = \
                        FolderModel(dataViewId=dataViewId,
                                    folder=datasetFolderName,
                                    location=userFolderPath,
                                    userFolderName=userFolderName,
                                    groupFolderName=groupFolderName,
                                    owner=owner,
                                    settingsModel=self.settingsModel)
                    folderModel.group = groupModel
                    folderModel.SetCreatedDate()
                    folderModel.experimentTitle = \
                        "%s - %s" % (self.settingsModel.general.instrumentName,
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

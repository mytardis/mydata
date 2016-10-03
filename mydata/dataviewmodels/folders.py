"""
Represents the Folders tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

# pylint: disable=wrong-import-position

import threading
import os
import sys
import traceback
from datetime import datetime
from glob import glob

import wx
if wx.version().startswith("3.0.3.dev"):
    from wx.dataview import DataViewIndexListModel  # pylint: disable=no-name-in-module
else:
    from wx.dataview import PyDataViewIndexListModel as DataViewIndexListModel

from mydata.models.folder import FolderModel
from mydata.models.user import UserModel
from mydata.models.group import GroupModel
from mydata.logs import logger
from mydata.utils.exceptions import InvalidFolderStructure
from mydata.utils.exceptions import DoesNotExist
from mydata.utils import EndBusyCursorIfRequired
import mydata.events as mde


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class FoldersModel(DataViewIndexListModel):
    """
    Represents the Folders tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    def __init__(self, usersModel, groupsModel, settingsModel):

        self.foldersData = []

        DataViewIndexListModel.__init__(self, len(self.foldersData))

        self.usersModel = usersModel
        self.groupsModel = groupsModel
        self.settingsModel = settingsModel

        # Unfiltered folders data:
        self.ufd = self.foldersData
        # Filtered folders data:
        self.ffd = list()
        self.filtered = False
        self.searchString = ""

        self.columnNames = ("Id", "Folder (dataset)", "Location", "Created",
                            "Experiment", "Status", "Owner", "Group")
        self.columnKeys = ("dataViewId", "folder", "location", "created",
                           "experimentTitle", "status",
                           "owner.username", "group.shortName")

        if sys.platform.startswith("win"):
            self.defaultColumnWidths = (40, 185, 200, 80, 150, 160, 90, 150)
        else:
            self.defaultColumnWidths = (40, 185, 200, 80, 160, 160, 90, 150)

        # This is the largest ID value which has been used in this model.
        # It may no longer exist, i.e. if we delete the row with the
        # largest ID, we don't decrement the maximum ID.
        self.maxDataViewId = 0

        self.ignoreIntervalSeconds = 0
        self.ignoreOldDatasets = False
        self.ignoreIntervalNumber = 0
        self.ignoreIntervalUnit = "months"

    def DeleteAllRows(self):
        """
        Delete all rows.
        """
        rowsDeleted = []
        for row in reversed(range(0, self.GetCount())):
            del self.foldersData[row]
            rowsDeleted.append(row)

        if threading.current_thread().name == "MainThread":
            self.RowsDeleted(rowsDeleted)
        else:
            wx.CallAfter(self.RowsDeleted, rowsDeleted)

        self.ufd = list()
        self.ffd = list()
        self.filtered = False
        self.searchString = ""
        self.maxDataViewId = 0

    def GetFolderRecord(self, row):
        """
        Return the folder model at a given row number (starting with row 0).
        """
        return self.foldersData[row]

    def CleanUp(self):
        """
        Perform clean up actions on each each folder model.
        """
        logger.debug("Cleaning up each FolderModel record's threads...")
        for row in range(0, self.GetRowCount()):
            self.foldersData[row].CleanUp()
        logger.debug("Cleaned up each FolderModel record's threads...")

    def GetSettingsModel(self):
        """
        Returns settings model.
        """
        return self.settingsModel

    # pylint: disable=too-many-branches
    def Filter(self, searchString):
        """
        Only show folders matching the query string, typed in the search box
        in the upper-right corner of the main window.
        """
        self.searchString = searchString
        query = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.ufd = list(self.foldersData)

        for row in reversed(range(0, self.GetRowCount())):
            fdata = self.foldersData[row]
            if query not in fdata.GetFolder().lower() and \
                    query not in fdata.GetLocation().lower() and \
                    query not in fdata.GetOwner().GetUsername().lower() and \
                    query not in fdata.GetExperimentTitle():
                self.ffd.append(fdata)
                del self.foldersData[row]
                # Notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            ffd = self.ffd[filteredRow]
            if query in ffd.GetFolder().lower() or \
                    query in ffd.GetLocation().lower() or \
                    query in ffd.GetOwner().GetUsername().lower() or \
                    query in ffd.GetExperimentTitle():
                # Model doesn't care about currently sorted column.
                # Always use ID.
                row = 0
                col = 0
                ascending = True  # Need to get current sort direction
                while row < self.GetRowCount() and \
                        self.CompareFolderRecords(self.foldersData[row],
                                                  self.ffd[filteredRow],
                                                  col, ascending) < 0:
                    row = row + 1

                if row == self.GetRowCount():
                    self.foldersData\
                        .append(self.ffd[filteredRow])
                    # Notify the view(s) using this model
                    # that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowAppended()
                    else:
                        wx.CallAfter(self.RowAppended)
                else:
                    self.foldersData.insert(
                        row, self.ffd[filteredRow])
                    # Notify the view(s) using this model
                    # that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowInserted(row)
                    else:
                        wx.CallAfter(self.RowInserted)
                del self.ffd[filteredRow]
                if self.GetFilteredRowCount() == 0:
                    self.filtered = False

    # pylint: disable=unused-argument
    # pylint: disable=arguments-differ
    def GetColumnType(self, col):
        """
        All of our columns are strings.  If the model or the renderers
        in the view are other types then that should be reflected here.
        """
        # pylint: disable=no-self-use
        return "string"

    # pylint: disable=arguments-differ
    def GetValueByRow(self, row, col):
        """
        This method is called to provide the foldersData object for a
        particular row,col
        """
        columnKey = self.GetColumnKeyName(col)
        if columnKey.startswith("owner."):
            ownerKey = columnKey.split("owner.")[1]
            owner = self.foldersData[row].GetOwner()
            if owner is not None:
                return owner.GetValueForKey(ownerKey)
            else:
                return ""
        elif columnKey.startswith("group."):
            groupKey = columnKey.split("group.")[1]
            group = self.foldersData[row].GetGroup()
            if group is not None:
                return group.GetValueForKey(groupKey)
            else:
                return ""
        return str(self.foldersData[row].GetValueForKey(columnKey))

    def GetValueForRowColumnKeyName(self, row, columnKeyName):
        """
        This method is called to provide the foldersData object for a
        particular row,columnKeyName
        """
        for col in range(0, self.GetColumnCount()):
            if self.GetColumnKeyName(col) == columnKeyName:
                return self.GetValueByRow(row, col)
        return None

    # pylint: disable=arguments-differ
    def GetColumnName(self, col):
        """
        Get column name.
        """
        return self.columnNames[col]

    def GetColumnKeyName(self, col):
        """
        Get column key name.
        """
        return self.columnKeys[col]

    def GetDefaultColumnWidth(self, col):
        """
        Get default column width.
        """
        return self.defaultColumnWidths[col]

    def GetFolderPath(self, row):
        """
        Get folder path.
        """
        return os.path.join(self.foldersData[row].GetLocation(),
                            self.foldersData[row].GetFolder())

    # pylint: disable=arguments-differ
    def GetRowCount(self):
        """
        Report how many rows this model provides data for.
        """
        return len(self.foldersData)

    def GetUnfilteredRowCount(self):
        """
        Report how many rows this model provides data for.
        """
        return len(self.ufd)

    def GetFilteredRowCount(self):
        """
        Report how many rows this model provides data for.
        """
        return len(self.ffd)

    # pylint: disable=arguments-differ
    def GetColumnCount(self):
        """
        Report how many columns this model provides data for.
        """
        return len(self.columnNames)

    def GetCount(self):
        """
        Report the number of rows in the model
        """
        return len(self.foldersData)

    # pylint: disable=unused-argument
    def GetAttrByRow(self, row, col, attr):
        """
        Called to check if non-standard attributes
        should be used in the cell at (row, col)
        """
        # pylint: disable=no-self-use
        if col == 4:
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False

    def Compare(self, item1, item2, col, ascending):
        """
        This is called to assist with sorting the data in the view.  The
        first two args are instances of the DataViewItem class, so we
        need to convert them to row numbers with the GetRow method.
        Then it's just a matter of fetching the right values from our
        data set and comparing them.  The return value is -1, 0, or 1,
        just like Python's cmp() function.
        """
        if not ascending:  # swap sort order?
            item2, item1 = item1, item2
        row1 = self.GetRow(item1)
        row2 = self.GetRow(item2)
        if col == 0:
            return cmp(int(self.GetValueByRow(row1, col)),
                       int(self.GetValueByRow(row2, col)))
        else:
            return cmp(self.GetValueByRow(row1, col),
                       self.GetValueByRow(row2, col))

    def CompareFolderRecords(self, folderRecord1, folderRecord2,
                             col, ascending):
        """
        Unlike the previous Compare method, in this case, the folder records
        don't need to be visible in the current (possibly filtered) data view.
        """
        if not ascending:  # swap sort order?
            folderRecord2, folderRecord1 = folderRecord1, folderRecord2
        if col == 0 or col == 3:
            return cmp(int(folderRecord1.GetDataViewId()),
                       int(folderRecord2.GetDataViewId()))
        else:
            return cmp(folderRecord1.GetValueForKey(self.columnKeys[col]),
                       folderRecord2.GetValueForKey(self.columnKeys[col]))

    def DeleteRows(self, rows):
        """
        Delete rows.
        """
        # Ensure that we save the largest ID used so far:
        self.GetMaxDataViewId()

        # make a copy since we'll be sorting(mutating) the list
        rows = list(rows)
        # use reverse order so the indexes don't change as we remove items
        rows.sort(reverse=True)

        for row in rows:
            del self.foldersData[row]
            del self.ufd[row]
            # Notify the view(s) using this model that it has been removed
            if threading.current_thread().name == "MainThread":
                self.RowDeleted(row)
            else:
                wx.CallAfter(self.RowDeleted, row)

    def DeleteFolderById(self, dataViewId):
        """
        Delete folder by ID.
        """
        # Ensure that we save the largest ID used so far:
        self.GetMaxDataViewId()

        for row in range(0, self.GetRowCount()):
            if self.foldersData[row].GetId() == dataViewId:
                del self.foldersData[row]
                # notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                return

    def GetMaxDataViewIdFromExistingRows(self):
        """
        Get maximum dataview ID from existing rows.
        """
        maxDataViewId = 0
        for row in range(0, self.GetCount()):
            if self.foldersData[row].GetDataViewId() > maxDataViewId:
                maxDataViewId = self.foldersData[row].GetDataViewId()
        return maxDataViewId

    def GetMaxDataViewId(self):
        """
        Get maximum dataview ID.
        """
        if self.GetMaxDataViewIdFromExistingRows() > self.maxDataViewId:
            self.maxDataViewId = self.GetMaxDataViewIdFromExistingRows()
        return self.maxDataViewId

    def TryRowValueChanged(self, row, col):
        """
        Use try/except when calling RowValueChanged, because
        sometimes there are timing issues which raise wx
        assertions suggesting that the row index we are trying
        to report a change on is greater than or equal to the
        total number of rows in the model.
        """
        try:
            if row < self.GetCount():
                self.RowValueChanged(row, col)
            else:
                logger.warning("TryRowValueChanged called with "
                               "row=%d, self.GetRowCount()=%d" %
                               (row, self.GetRowCount()))
                self.RowValueChanged(row, col)
        except wx.PyAssertionError:
            logger.warning(traceback.format_exc())

    def AddRow(self, folderModel):
        """
        Add folder model to folders model and notify view.
        """
        self.Filter("")
        self.foldersData.append(folderModel)
        # Notify views
        if threading.current_thread().name == "MainThread":
            self.RowAppended()
        else:
            wx.CallAfter(self.RowAppended)

        self.ufd = self.foldersData
        self.ffd = list()
        self.Filter(self.searchString)

        if hasattr(wx.GetApp(), "GetMainFrame"):
            startDataUploadsForFolderEvent = \
                mde.MyDataEvent(mde.EVT_START_UPLOADS_FOR_FOLDER,
                                folderModel=folderModel)
            wx.PostEvent(wx.GetApp().GetMainFrame(),
                         startDataUploadsForFolderEvent)

    def FolderStatusUpdated(self, folderModel):
        """
        Ensure that updated folder status is reflected in the view.
        """
        for row in range(0, self.GetCount()):
            if self.foldersData[row] == folderModel:
                col = self.columnNames.index("Status")
                if threading.current_thread().name == "MainThread":
                    self.TryRowValueChanged(row, col)
                else:
                    wx.CallAfter(self.TryRowValueChanged, row, col)

    def ScanFolders(self, incrementProgressDialog, shouldAbort):
        """
        Scan dataset folders.
        """
        if self.GetCount() > 0:
            self.DeleteAllRows()
        if self.usersModel.GetCount() > 0:
            self.usersModel.DeleteAllRows()
        if self.groupsModel.GetCount() > 0:
            self.groupsModel.DeleteAllRows()
        dataDir = self.settingsModel.GetDataDirectory()
        defaultOwner = self.settingsModel.GetDefaultOwner()
        folderStructure = self.settingsModel.GetFolderStructure()
        self.ignoreOldDatasets = self.settingsModel.IgnoreOldDatasets()
        if self.ignoreOldDatasets:
            seconds = {}
            seconds['day'] = 24 * 60 * 60
            seconds['week'] = 7 * seconds['day']
            seconds['year'] = int(365.25 * seconds['day'])
            seconds['month'] = seconds['year'] / 12
            singularIgnoreIntervalUnit = \
                self.settingsModel.GetIgnoreOldDatasetIntervalUnit().rstrip(
                    's')
            ignoreIntervalUnitSeconds = seconds[singularIgnoreIntervalUnit]

            self.ignoreIntervalNumber = \
                self.settingsModel.GetIgnoreOldDatasetIntervalNumber()
            self.ignoreIntervalUnit = \
                self.settingsModel.GetIgnoreOldDatasetIntervalUnit()
            self.ignoreIntervalSeconds = \
                self.ignoreIntervalNumber * ignoreIntervalUnitSeconds
        logger.debug("FoldersModel.ScanFolders(): Scanning " + dataDir + "...")
        if folderStructure.startswith("Username") or \
                folderStructure.startswith("Email"):
            self.ScanForUserFolders(incrementProgressDialog, shouldAbort)
        elif folderStructure.startswith("User Group"):
            self.ScanForGroupFolders(incrementProgressDialog, shouldAbort)
        elif folderStructure.startswith("Experiment"):
            self.ScanForExperimentFolders(dataDir, defaultOwner,
                                          defaultOwner.GetUsername())
        elif folderStructure.startswith("Dataset"):
            self.ScanForDatasetFolders(dataDir, defaultOwner,
                                       defaultOwner.GetUsername())
        else:
            raise InvalidFolderStructure("Unknown folder structure.")

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def ScanForUserFolders(self, incrementProgressDialog, shouldAbort):
        """
        Scan for user folders.
        """
        dataDir = self.settingsModel.GetDataDirectory()
        userOrGroupFilterString = '*%s*' % self.settingsModel.GetUserFilter()
        folderStructure = self.settingsModel.GetFolderStructure()
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
            usersDataViewId = self.usersModel.GetMaxDataViewId() + 1
            try:
                if folderStructure.startswith("Username"):
                    userRecord = \
                        UserModel.GetUserByUsername(self.settingsModel,
                                                    userFolderName)
                elif folderStructure.startswith("Email"):
                    userRecord = \
                        UserModel.GetUserByEmail(self.settingsModel,
                                                 userFolderName)

            except DoesNotExist:
                userRecord = None
            if shouldAbort():
                wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage,
                             "Data scans and uploads were canceled.")
                wx.CallAfter(EndBusyCursorIfRequired)
                return
            if userRecord is not None:
                userRecord.SetDataViewId(usersDataViewId)
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
            else:
                message = "Didn't find a MyTardis user record for folder " \
                    "\"%s\" in %s" % (userFolderName, dataDir)
                logger.warning(message)
                if shouldAbort():
                    wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage,
                                 "Data scans and uploads were canceled.")
                    wx.CallAfter(EndBusyCursorIfRequired)
                    return
                if not self.settingsModel.UploadInvalidUserOrGroupFolders():
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
                userRecord.SetDataViewId(usersDataViewId)
                self.usersModel.AddRow(userRecord)
                if shouldAbort():
                    wx.CallAfter(wx.GetApp().GetMainFrame().SetStatusMessage,
                                 "Data scans and uploads were canceled.")
                    wx.CallAfter(EndBusyCursorIfRequired)
                    return
                self.ScanForDatasetFolders(os.path.join(dataDir,
                                                        userFolderName),
                                           userRecord, userFolderName)
            if threading.current_thread().name == "MainThread":
                incrementProgressDialog()
            else:
                wx.CallAfter(incrementProgressDialog)

    def ScanForGroupFolders(self, incrementProgressDialog, shouldAbort):
        """
        Scan for group folders.
        """
        dataDir = self.settingsModel.GetDataDirectory()
        userOrGroupFilterString = '*%s*' % self.settingsModel.GetUserFilter()
        filesDepth1 = glob(os.path.join(dataDir, userOrGroupFilterString))
        dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
        groupFolderNames = [os.path.basename(d) for d in dirsDepth1]
        folderStructure = self.settingsModel.GetFolderStructure()
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
                groupName = self.settingsModel.GetGroupPrefix() + \
                    groupFolderName
                groupRecord = \
                    GroupModel.GetGroupByName(self.settingsModel,
                                              groupName)
            except DoesNotExist:
                groupRecord = None
                message = "Didn't find a MyTardis user group record for " \
                    "folder \"%s\" in %s" % (groupFolderName,
                                             dataDir)
                logger.warning(message)
                if not self.settingsModel.UploadInvalidUserOrGroupFolders():
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
                groupRecord.SetDataViewId(groupsDataViewId)
                self.groupsModel.AddRow(groupRecord)
            groupFolderPath = os.path.join(dataDir, groupFolderName)
            if folderStructure == \
                    'User Group / Instrument / Full Name / Dataset':
                self.ImportGroupFolders(groupFolderPath, groupRecord)
            elif folderStructure == 'User Group / Experiment / Dataset':
                defaultOwner = self.settingsModel.GetDefaultOwner()
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
                incrementProgressDialog()
            else:
                wx.CallAfter(incrementProgressDialog)

    def ScanForDatasetFolders(self, pathToScan, owner, userFolderName):
        """
        Scan for dataset folders.
        """
        # pylint: disable=bare-except
        try:
            logger.debug("Scanning " + pathToScan +
                         " for dataset folders...")
            datasetFilterString = \
                '*%s*' % self.settingsModel.GetDatasetFilter()
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
                                foldersModel=self,
                                usersModel=self.usersModel,
                                settingsModel=self.settingsModel)
                folderModel.SetCreatedDate()
                if not owner.UserNotFoundInMyTardis():
                    if owner.GetName().strip() != "":
                        experimentTitle = "%s - %s" \
                            % (self.settingsModel.GetInstrumentName(),
                               owner.GetName())
                    else:
                        experimentTitle = "%s - %s" \
                            % (self.settingsModel.GetInstrumentName(),
                               owner.GetUsername())
                elif owner.GetName() != UserModel.userNotFoundString:
                    experimentTitle = "%s - %s (%s)" \
                        % (self.settingsModel.GetInstrumentName(),
                           owner.GetName(),
                           UserModel.userNotFoundString)
                elif owner.GetUsername() != UserModel.userNotFoundString:
                    experimentTitle = "%s - %s (%s)" \
                        % (self.settingsModel.GetInstrumentName(),
                           owner.GetUsername(),
                           UserModel.userNotFoundString)
                elif owner.GetEmail() != UserModel.userNotFoundString:
                    experimentTitle = "%s - %s (%s)" \
                        % (self.settingsModel.GetInstrumentName(),
                           owner.GetEmail(),
                           UserModel.userNotFoundString)
                else:
                    experimentTitle = "%s - %s" \
                        % (self.settingsModel.GetInstrumentName(),
                           UserModel.userNotFoundString)
                folderModel.SetExperimentTitle(experimentTitle)
                self.AddRow(folderModel)
        except:
            logger.error(traceback.format_exc())

    def ScanForExperimentFolders(self, pathToScan, owner,
                                 userFolderName=None,
                                 groupRecord=None, groupFolderName=None):
        # pylint: disable=too-many-arguments
        """
        Scans for experiment folders.

        The MyTardis role account specified in the Settings dialog will
        automatically be given access (and ownership) to every experiment
        created.  If the experiment folder is found within a user folder,
        then that user will be given access, and similarly, if it is
        found within a user group folder, then the user group will be
        given access.
        """
        datasetFilterString = '*%s*' % self.settingsModel.GetDatasetFilter()
        expFilterString = '*%s*' % self.settingsModel.GetExperimentFilter()
        filesDepth1 = glob(os.path.join(pathToScan, expFilterString))
        dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
        expFolders = [os.path.basename(d) for d in dirsDepth1]
        folderStructure = self.settingsModel.GetFolderStructure()
        for expFolderName in expFolders:
            expFolderPath = os.path.join(pathToScan, expFolderName)
            filesDepth1 = glob(os.path.join(expFolderPath,
                                            datasetFilterString))
            dirsDepth1 = [item for item in filesDepth1 if os.path.isdir(item)]
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
                if folderStructure.startswith("Username") or \
                        folderStructure.startswith("Email") or \
                        folderStructure.startswith("Experiment"):
                    folderModel = \
                        FolderModel(dataViewId=dataViewId,
                                    folder=datasetFolderName,
                                    location=expFolderPath,
                                    userFolderName=userFolderName,
                                    groupFolderName=None,
                                    owner=owner,
                                    foldersModel=self,
                                    usersModel=self.usersModel,
                                    settingsModel=self.settingsModel)
                    folderModel.SetExperimentTitle(expFolderName)
                elif folderStructure.startswith("User Group"):
                    folderModel = \
                        FolderModel(dataViewId=dataViewId,
                                    folder=datasetFolderName,
                                    location=expFolderPath,
                                    userFolderName=None,
                                    groupFolderName=groupFolderName,
                                    owner=owner,
                                    foldersModel=self,
                                    usersModel=self.usersModel,
                                    settingsModel=self.settingsModel)
                    folderModel.SetGroup(groupRecord)
                    if groupRecord:
                        groupName = groupRecord.GetShortName()
                    else:
                        groupName = groupFolderName
                    folderModel.SetExperimentTitle(
                        "%s - %s" % (groupName, expFolderName))
                else:
                    raise InvalidFolderStructure("Unknown folder structure.")
                folderModel.SetCreatedDate()
                self.AddRow(folderModel)

    def ImportGroupFolders(self, groupFolderPath, groupModel):
        """
        Scan folders within a user group folder,
        e.g. D:\\Data\\Smith-Lab\\
        """
        # pylint: disable=bare-except
        try:
            logger.debug("Scanning " + groupFolderPath +
                         " for instrument folders...")
            datasetFilterString = \
                '*%s*' % self.settingsModel.GetDatasetFilter()
            instrumentName = self.settingsModel.GetInstrumentName()
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

            # Rather than using any folder we happen to find at this level,
            # we will use the instrument name specified in MyData's Settings
            # dialog.  That way, we can run MyData on a collection of data
            # from multiple instruments, and just select one instrument at
            # a time.
            instrumentFolderPath = \
                os.path.join(groupFolderPath,
                             self.settingsModel.GetInstrumentName())

            if not os.path.exists(instrumentFolderPath):
                logger.warning("Path %s doesn't exist." % instrumentFolderPath)
                return

            # For the User Group / Instrument / Researcher's Name / Dataset
            # folder structure, the default owner in MyTardis will always
            # by the user listed in MyData's settings dialog.  An additional
            # ObjectACL will be created in MyTardis to grant access to the
            # User Group.  The researcher's name in this folder structure is
            # used to determine the default experiment name, but it is not
            # used to determine access control.
            owner = self.settingsModel.GetDefaultOwner()

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
                                    foldersModel=self,
                                    usersModel=self.usersModel,
                                    settingsModel=self.settingsModel)
                    folderModel.SetGroup(groupModel)
                    folderModel.SetCreatedDate()
                    folderModel.SetExperimentTitle(
                        "%s - %s" % (self.settingsModel.GetInstrumentName(),
                                     userFolderName))
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
        for folderModel in self.foldersData:
            total += folderModel.GetNumFiles()
        return total

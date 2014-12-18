import wx
import wx.dataview
import sqlite3
from FolderModel import FolderModel
from ExperimentModel import ExperimentModel
import threading
import os
import sys
import traceback

from logger.Logger import logger

# This model class provides the data to the view when it is asked for.
# Since it is a list-only model (no hierachical data) then it is able
# to be referenced by row rather than by item object, so in this way
# it is easier to comprehend and use than other model types.  In this
# example we also provide a Compare function to assist with sorting of
# items in our model.  Notice that the data items in the data model
# object don't ever change position due to a sort or column
# reordering.  The view manages all of that and maps view rows and
# columns to the model's rows and columns as needed.
#
# Our data is stored in a list of FolderModel objects.


def GetFolderTypes():
    return ['User', 'Experiment', 'Dataset']


class FoldersModel(wx.dataview.PyDataViewIndexListModel):
    def __init__(self, sqlitedb, usersModel, settingsModel):

        self.sqlitedb = sqlitedb

        self.foldersData = []

        # Earlier prototypes loaded the last used folder view from an Sqlite
        # database on disk, recording the folders which the user had
        # previously dragged and dropped into the application.  Whereas now
        # it scans the root data directory and constructs the folder list from
        # scratch every time.

        wx.dataview.PyDataViewIndexListModel.__init__(self,
                                                      len(self.foldersData))

        self.usersModel = usersModel
        self.settingsModel = settingsModel

        # Unfiltered folders data:
        self.ufd = self.foldersData
        # Filtered folders data:
        self.ffd = list()
        self.filtered = False
        self.searchString = ""

        self.columnNames = ("Id", "Folder", "Location", "Created", "Status",
                            "Owner", "Email")
        self.columnKeys = ("dataViewId", "folder", "location", "created",
                           "status", "owner.username", "owner.email")

        if sys.platform.startswith("win"):
            self.defaultColumnWidths = (40, 185, 200, 70, 160, 120, 180)
        else:
            self.defaultColumnWidths = (40, 185, 200, 80, 160, 120, 180)

        # This is the largest ID value which has been used in this model.
        # It may no longer exist, i.e. if we delete the row with the
        # largest ID, we don't decrement the maximum ID.
        self.maxDataViewId = 0

    def DeleteAllRows(self):
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
        return self.foldersData[row]

    def CleanUp(self):
        logger.debug("Joining FoldersModel's UploadDataThread...")
        self.uploadDataThread.join()
        logger.debug("Joined FoldersModel's UploadDataThread.")

        logger.debug("Cleaning up each FolderModel record's threads...")
        for row in range(0, self.GetRowCount()):
            self.foldersData[row].CleanUp()
        logger.debug("Cleaned up each FolderModel record's threads...")

    def GetSettingsModel(self):
        return self.settingsModel

    def Filter(self, searchString):
        self.searchString = searchString
        q = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.ufd = list(self.foldersData)

        for row in reversed(range(0, self.GetRowCount())):
            fd = self.foldersData[row]
            if q not in fd.GetFolder().lower() and \
                    q not in fd.GetLocation().lower() and \
                    q not in fd.GetOwner().GetUsername().lower() and \
                    q not in fd.GetCreated():
                self.ffd.append(fd)
                del self.foldersData[row]
                # Notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            ffd = self.ffd[filteredRow]
            if q in ffd.GetFolder().lower() or \
                    q in ffd.GetLocation().lower() or \
                    q in ffd.GetOwner().GetUsername().lower() or \
                    q in ffd.GetCreated():
                # Model doesn't care about currently sorted column.
                # Always use ID.
                row = 0
                col = 0
                ascending = True  # Need to get current sort direction
                while row < self.GetRowCount() and \
                        self.CompareFolderRecords(
                            self.foldersData[row],
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

    # All of our columns are strings.  If the model or the renderers
    # in the view are other types then that should be reflected here.
    def GetColumnType(self, col):
        return "string"

    # This method is called to provide the foldersData object for a
    # particular row,col
    def GetValueByRow(self, row, col):
        columnKey = self.GetColumnKeyName(col)
        if columnKey.startswith("owner."):
            ownerKey = columnKey.split("owner.")[1]
            owner_id = self.foldersData[row].GetValueForKey('owner_id')
            owner = self.usersModel.GetUserById(id=owner_id)
            if owner is not None:
                return owner.GetValueForKey(ownerKey)
            else:
                return None
        return str(self.foldersData[row].GetValueForKey(columnKey))

    # This method is called to provide the foldersData object for a
    # particular row,colname
    def GetValueForRowColname(self, row, colname):
        for col in range(0, self.GetColumnCount()):
            if self.GetColumnName(col) == colname:
                return self.GetValueByRow(row, col)
        return None

    def GetColumnName(self, col):
        return self.columnNames[col]

    def GetColumnKeyName(self, col):
        return self.columnKeys[col]

    def GetDefaultColumnWidth(self, col):
        return self.defaultColumnWidths[col]

    def GetFolderPath(self, row):
        import os
        return os.path.join(self.foldersData[row].GetLocation(),
                            self.foldersData[row].GetFolder())

    # Report how many rows this model provides data for.
    def GetRowCount(self):
        return len(self.foldersData)

    # Report how many rows this model provides data for.
    def GetUnfilteredRowCount(self):
        return len(self.ufd)

    # Report how many rows this model provides data for.
    def GetFilteredRowCount(self):
        return len(self.ffd)

    # Report how many columns this model provides data for.
    def GetColumnCount(self):
        return len(self.columnNames)

    # Report the number of rows in the model
    def GetCount(self):
        return len(self.foldersData)

    # Called to check if non-standard attributes should be used in the
    # cell at (row, col)
    def GetAttrByRow(self, row, col, attr):
        if col == 4:
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False

    # This is called to assist with sorting the data in the view.  The
    # first two args are instances of the DataViewItem class, so we
    # need to convert them to row numbers with the GetRow method.
    # Then it's just a matter of fetching the right values from our
    # data set and comparing them.  The return value is -1, 0, or 1,
    # just like Python's cmp() function.
    def Compare(self, item1, item2, col, ascending):
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

    # Unlike the previous Compare method, in this case, the folder records
    # don't need to be visible in the current (possibly filtered) data view.
    def CompareFolderRecords(self, folderRecord1, folderRecord2,
                             col, ascending):
        if not ascending:  # swap sort order?
            folderRecord2, folderRecord1 = folderRecord1, folderRecord2
        if col == 0 or col == 3:
            return cmp(int(folderRecord1.GetId()), int(folderRecord2.GetId()))
        else:
            return cmp(folderRecord1.GetValueForKey(self.columnKeys[col]),
                       folderRecord2.GetValueForKey(self.columnKeys[col]))

    def DeleteRows(self, rows):
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

    def DeleteFolderById(self, id):
        # Ensure that we save the largest ID used so far:
        self.GetMaxDataViewId()

        for row in range(0, self.GetRowCount()):
            if self.foldersData[row].GetId() == id:
                del self.foldersData[row]
                # notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                return

    def Contains(self, path):
        import os
        from Win32SamePath import Win32SamePath
        win32SamePath = Win32SamePath()
        dir1 = path
        for row in range(0, self.GetCount()):

            dir2 = self.GetFolderPath(row)
            if win32SamePath.paths_are_equal(dir1, dir2):
                return True
        return False

    def GetMaxDataViewIdFromExistingRows(self):
        maxDataViewId = 0
        for row in range(0, self.GetCount()):
            if self.foldersData[row].GetDataViewId() > maxDataViewId:
                maxDataViewId = self.foldersData[row].GetDataViewId()
        return maxDataViewId

    def GetMaxDataViewId(self):
        if self.GetMaxDataViewIdFromExistingRows() > self.maxDataViewId:
            self.maxDataViewId = self.GetMaxDataViewIdFromExistingRows()
        return self.maxDataViewId

    def AddRow(self, value):
        self.Filter("")
        self.foldersData.append(value)
        # Notify views
        if threading.current_thread().name == "MainThread":
            self.RowAppended()
        else:
            wx.CallAfter(self.RowAppended)

        self.ufd = self.foldersData
        self.ffd = list()
        self.Filter(self.searchString)

    def Refresh(self):
        # Only recalculate number of files (uploaded) per folder for now.
        col = 3
        for row in range(0, self.GetRowCount()):
            modified = self.foldersData[row].Refresh()
            if modified:
                if threading.current_thread().name == "MainThread":
                    self.RowValueChanged(row, col)
                else:
                    wx.CallAfter(self.RowValueChanged, row, col)

    def FolderStatusUpdated(self, folderModel):
        for row in range(0, self.GetCount()):
            if self.foldersData[row] == folderModel:
                col = self.columnNames.index("Status")
                if threading.current_thread().name == "MainThread":
                    self.RowValueChanged(row, col)
                else:
                    wx.CallAfter(self.RowValueChanged, row, col)

    def ImportFolders(self, dataDirectory, owner):
      try:
        logger.debug("Scanning " + dataDirectory + " for dataset folders...")
        datasetFolders = os.walk(dataDirectory).next()[1]
        for datasetFolder in datasetFolders:
            dataViewId = self.GetMaxDataViewId() + 1
            folderModel = FolderModel(dataViewId=dataViewId,
                                      folder=datasetFolder,
                                      location=dataDirectory,
                                      folder_type='Dataset',
                                      owner_id=owner.GetId(),
                                      foldersModel=self,
                                      usersModel=self.usersModel,
                                      settingsModel=self.settingsModel)
            folderModel.SetCreatedDate()
            self.AddRow(folderModel)
      except:
        print traceback.format_exc()

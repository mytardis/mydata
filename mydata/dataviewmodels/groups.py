"""
Represents the Groups tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

# pylint: disable=missing-docstring

import threading

import wx
if wx.version().startswith("3.0.3.dev"):
    from wx.dataview import DataViewIndexListModel  # pylint: disable=no-name-in-module
else:
    from wx.dataview import PyDataViewIndexListModel as DataViewIndexListModel


class GroupsModel(DataViewIndexListModel):
    """
    Represents the Groups tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    def __init__(self, settingsModel):
        self.settingsModel = settingsModel
        self.foldersModel = None

        self.groupsData = list()

        DataViewIndexListModel.__init__(self, len(self.groupsData))

        self.unfilteredGroupsData = self.groupsData
        self.filteredGroupsData = list()
        self.filtered = False
        self.searchString = ""

        self.columnNames = ("Id", "Short Name", "Full Name")
        self.columnKeys = ("dataViewId", "shortName", "name")
        self.defaultColumnWidths = (40, 200, 400)

        # This is the largest ID value which has been used in this model.
        # It may no longer exist, i.e. if we delete the row with the
        # largest ID, we don't decrement the maximum ID.
        self.maxDataViewId = 0

    def SetFoldersModel(self, foldersModel):
        self.foldersModel = foldersModel

    def Filter(self, searchString):
        # pylint: disable=too-many-branches
        self.searchString = searchString
        query = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.unfilteredGroupsData = list(self.groupsData)

        for row in reversed(range(0, self.GetRowCount())):
            if query not in self.groupsData[row].GetName().lower():
                self.filteredGroupsData.append(self.groupsData[row])
                del self.groupsData[row]
                # notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            fgd = self.filteredGroupsData[filteredRow]
            if query in fgd.GetName().lower():
                # Model doesn't care about currently sorted column.
                # Always use ID.
                row = 0
                col = 0
                # Need to get current sort direction
                ascending = True
                while row < self.GetRowCount() and \
                        self.CompareGroupRecords(self.groupsData[row],
                                                 fgd, col, ascending) < 0:
                    row += 1

                if row == self.GetRowCount():
                    self.groupsData.append(fgd)
                    # Notify the view using this model that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowAppended()
                    else:
                        wx.CallAfter(self.RowAppended)
                else:
                    self.groupsData.insert(row, fgd)
                    # Notify the view using this model that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowInserted(row)
                    else:
                        wx.CallAfter(self.RowInserted, row)
                del self.filteredGroupsData[filteredRow]
                if self.GetFilteredRowCount() == 0:
                    self.filtered = False

    def GetColumnType(self, col):
        """
        All of our columns are strings.  If the model or the renderers
        in the view are other types then that should be reflected here.
        """
        # pylint: disable=arguments-differ
        # pylint: disable=unused-argument
        # pylint: disable=no-self-use
        return "string"

    def GetValueByRow(self, row, col):
        """
        This method is called to provide the groupsData object
        for a particular row, col
        """
        # pylint: disable=arguments-differ
        columnKey = self.GetColumnKeyName(col)
        return str(self.groupsData[row].GetValueForKey(columnKey))

    def GetValuesForColname(self, colname):
        values = []
        col = -1
        for col in range(0, self.GetColumnCount()):
            if self.GetColumnName(col) == colname:
                break
        if col == self.GetColumnCount():
            return None

        for row in range(0, self.GetRowCount()):
            values.append(self.GetValueByRow(row, col))
        return values

    def GetColumnName(self, col):
        return self.columnNames[col]

    def GetColumnKeyName(self, col):
        return self.columnKeys[col]

    def GetDefaultColumnWidth(self, col):
        return self.defaultColumnWidths[col]

    def GetRowCount(self):
        """
        Report how many rows this model provides data for.
        """
        return len(self.groupsData)

    def GetUnfilteredRowCount(self):
        return len(self.unfilteredGroupsData)

    def GetFilteredRowCount(self):
        """
        Report how many rows this model provides data for.
        """
        # pylint: disable=arguments-differ
        return len(self.filteredGroupsData)

    def GetColumnCount(self):
        """
        Report how many columns this model provides data for.
        """
        # pylint: disable=arguments-differ
        return len(self.columnNames)

    def GetCount(self):
        """
        Report the number of rows in the model
        """
        # pylint: disable=arguments-differ
        return len(self.groupsData)

    def GetAttrByRow(self, row, col, attr):
        """
        Called to check if non-standard attributes should be
        used in the cell at (row, col)
        """
        # pylint: disable=arguments-differ
        # pylint: disable=unused-argument
        # pylint: disable=no-self-use
        return False

    # This is called to assist with sorting the data in the view.  The
    # first two args are instances of the DataViewItem class, so we
    # need to convert them to row numbers with the GetRow method.
    # Then it's just a matter of fetching the right values from our
    # data set and comparing them.  The return value is -1, 0, or 1,
    # just like Python's cmp() function.
    def Compare(self, item1, item2, col, ascending):
        # pylint: disable=arguments-differ
        # Swap sort order?
        if not ascending:
            item2, item1 = item1, item2
        row1 = self.GetRow(item1)
        row2 = self.GetRow(item2)
        if col == 0:
            return cmp(int(self.GetValueByRow(row1, col)),
                       int(self.GetValueByRow(row2, col)))
        else:
            return cmp(self.GetValueByRow(row1, col),
                       self.GetValueByRow(row2, col))

    # Unlike the previous Compare method, in this case, the group records
    # don't need to be visible in the current (possibly filtered) data view.
    def CompareGroupRecords(self, groupRecord1, groupRecord2, col, ascending):
        # Swap sort order?
        if not ascending:
            groupRecord2, groupRecord1 = groupRecord1, groupRecord2
        if col == 0 or col == 3:
            return cmp(int(groupRecord1.GetDataViewId()),
                       int(groupRecord2.GetDataViewId()))
        else:
            return cmp(groupRecord1.GetValueForKey(self.columnKeys[col]),
                       groupRecord2.GetValueForKey(self.columnKeys[col]))

    def DeleteAllRows(self):
        rowsDeleted = []
        for row in reversed(range(0, self.GetCount())):
            del self.groupsData[row]
            rowsDeleted.append(row)

        # notify the view(s) using this model that it has been removed
        if threading.current_thread().name == "MainThread":
            self.RowsDeleted(rowsDeleted)
        else:
            wx.CallAfter(self.RowsDeleted, rowsDeleted)

        self.unfilteredGroupsData = list()
        self.filteredGroupsData = list()
        self.filtered = False
        self.searchString = ""
        self.maxDataViewId = 0

    def GetGroupById(self, dataViewId):
        for row in range(0, self.GetRowCount()):
            if self.unfilteredGroupsData[row].GetId() == dataViewId:
                return self.unfilteredGroupsData[row]
        return None

    def GetGroupByName(self, name):
        for row in range(0, self.GetRowCount()):
            if self.unfilteredGroupsData[row].GetName() == name:
                return self.unfilteredGroupsData[row]
        return None

    def GetMaxDataViewIdFromExistingRows(self):
        maxDataViewId = 0
        for row in range(0, self.GetCount()):
            if self.groupsData[row].GetDataViewId() > maxDataViewId:
                maxDataViewId = self.groupsData[row].GetDataViewId()
        return maxDataViewId

    def GetMaxDataViewId(self):
        if self.GetMaxDataViewIdFromExistingRows() > self.maxDataViewId:
            self.maxDataViewId = self.GetMaxDataViewIdFromExistingRows()
        return self.maxDataViewId

    def AddRow(self, value):
        self.Filter("")
        self.groupsData.append(value)
        # Notify views
        if threading.current_thread().name == "MainThread":
            self.RowAppended()
        else:
            wx.CallAfter(self.RowAppended)

        self.unfilteredGroupsData = self.groupsData
        self.filteredGroupsData = list()
        self.Filter(self.searchString)

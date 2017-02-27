"""
Represents the Users tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import os
import threading

import wx

from ..utils import Compare
from .dataview import MyDataDataViewModel


class UsersModel(MyDataDataViewModel):
    """
    Represents the Users tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=arguments-differ
    def __init__(self, settingsModel):
        super(UsersModel, self).__init__()

        self.settingsModel = settingsModel

        self.columnNames = ["Id", "Username", "Name", "Email"]
        self.columnKeys = ["dataViewId", "username", "name", "email"]
        self.defaultColumnWidths = [40, 100, 200, 260]

    def Filter(self, searchString):
        """
        Only show users matching the query string, typed in the search box
        in the upper-right corner of the main window.
        """
        # pylint: disable=too-many-branches
        self.searchString = searchString
        query = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.unfilteredData = list(self.rowsData)

        for row in reversed(range(0, self.GetRowCount())):
            if query not in self.rowsData[row].GetUsername().lower() and \
                    query not in self.rowsData[row].GetName().lower() and \
                    query not in self.rowsData[row].GetEmail().lower():
                self.filteredData.append(self.rowsData[row])
                del self.rowsData[row]
                # notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            fud = self.filteredData[filteredRow]
            if query in fud.GetName().lower() or \
                    query in fud.GetUsername().lower() or \
                    query in fud.GetEmail().lower():
                # Model doesn't care about currently sorted column.
                # Always use ID.
                row = 0
                col = 0
                # Need to get current sort direction
                ascending = True
                while row < self.GetRowCount() and \
                        self.Compare(self.rowsData[row],
                                     fud, col, ascending) < 0:
                    row += 1

                if row == self.GetRowCount():
                    self.rowsData.append(fud)
                    # Notify the view using this model that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowAppended()
                    else:
                        wx.CallAfter(self.RowAppended)
                else:
                    self.rowsData.insert(row, fud)
                    # Notify the view using this model that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowInserted(row)
                    else:
                        wx.CallAfter(self.RowInserted, row)
                del self.filteredData[filteredRow]
                if self.GetFilteredRowCount() == 0:
                    self.filtered = False

    def Compare(self, userRecord1, userRecord2, col, ascending):
        """
        This is called to assist with sorting the data in the view.  The
        first two args are instances of the DataViewItem class, so we
        need to convert them to row numbers with the GetRow method.
        Then it's just a matter of fetching the right values from our
        data set and comparing them.  The return value is -1, 0, or 1,
        just like Python's cmp() function.
        """
        try:
            userRecord1 = self.rowsData[self.GetRow(userRecord1)]
            userRecord2 = self.rowsData[self.GetRow(userRecord2)]
        except TypeError:
            # Compare is also called by Filter in which case we
            # don't need to convert from DataViewItem to UserModel.
            pass
        if not ascending:
            userRecord2, userRecord1 = userRecord1, userRecord2
        if col == 0 or col == 3:
            return Compare(int(userRecord1.dataViewId),
                           int(userRecord2.dataViewId))
        else:
            return Compare(userRecord1.GetValueForKey(self.columnKeys[col]),
                           userRecord2.GetValueForKey(self.columnKeys[col]))

    def GetNumUserOrGroupFolders(self):
        """
        Get number of user or group folders.

        Fast method, ignoring filters.
        """
        dataDir = self.settingsModel.general.dataDirectory
        userOrGroupFolderNames = os.walk(dataDir).next()[1]
        return len(userOrGroupFolderNames)

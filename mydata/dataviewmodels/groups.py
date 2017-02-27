"""
Represents the Groups tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import threading

import wx

from ..utils import Compare
from .dataview import MyDataDataViewModel


class GroupsModel(MyDataDataViewModel):
    """
    Represents the Groups tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=arguments-differ
    def __init__(self, settingsModel):
        super(GroupsModel, self).__init__()

        self.settingsModel = settingsModel

        self.columnNames = ["Id", "Short Name", "Full Name"]
        self.columnKeys = ["dataViewId", "shortName", "name"]
        self.defaultColumnWidths = [40, 200, 400]

    def Filter(self, searchString):
        """
        Only show groups matching the query string, typed in the search box
        in the upper-right corner of the main window.
        """
        # pylint: disable=too-many-branches
        self.searchString = searchString
        query = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.unfilteredData = list(self.rowsData)

        for row in reversed(range(0, self.GetRowCount())):
            if query not in self.rowsData[row].GetName().lower():
                self.filteredData.append(self.rowsData[row])
                del self.rowsData[row]
                # notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            fgd = self.filteredData[filteredRow]
            if query in fgd.GetName().lower():
                # Model doesn't care about currently sorted column.
                # Always use ID.
                row = 0
                col = 0
                # Need to get current sort direction
                ascending = True
                while row < self.GetRowCount() and \
                        self.Compare(self.rowsData[row],
                                     fgd, col, ascending) < 0:
                    row += 1

                if row == self.GetRowCount():
                    self.rowsData.append(fgd)
                    # Notify the view using this model that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowAppended()
                    else:
                        wx.CallAfter(self.RowAppended)
                else:
                    self.rowsData.insert(row, fgd)
                    # Notify the view using this model that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowInserted(row)
                    else:
                        wx.CallAfter(self.RowInserted, row)
                del self.filteredData[filteredRow]
                if self.GetFilteredRowCount() == 0:
                    self.filtered = False

    def Compare(self, groupRecord1, groupRecord2, col, ascending):
        """
        This is called to assist with sorting the data in the view.  The
        first two args are instances of the DataViewItem class, so we
        need to convert them to row numbers with the GetRow method.
        Then it's just a matter of fetching the right values from our
        data set and comparing them.  The return value is -1, 0, or 1,
        just like Python 2's cmp() function.
        """
        try:
            groupRecord1 = self.rowsData[self.GetRow(groupRecord1)]
            groupRecord2 = self.rowsData[self.GetRow(groupRecord2)]
        except TypeError:
            # Compare is also called by Filter in which case we
            # don't need to convert from DataViewItem to GroupModel.
            pass
        if not ascending:
            groupRecord2, groupRecord1 = groupRecord1, groupRecord2
        if col == 0 or col == 3:
            return Compare(int(groupRecord1.dataViewId),
                           int(groupRecord2.dataViewId))
        else:
            return Compare(groupRecord1.GetValueForKey(self.columnKeys[col]),
                           groupRecord2.GetValueForKey(self.columnKeys[col]))

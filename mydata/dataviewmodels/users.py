"""
Represents the Users tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import os

from ..settings import SETTINGS
from ..utils import Compare
from .dataview import MyDataDataViewModel


class UsersModel(MyDataDataViewModel):
    """
    Represents the Users tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=arguments-differ
    def __init__(self):
        super(UsersModel, self).__init__()
        self.columnNames = ["Id", "Username", "Name", "Email"]
        self.columnKeys = ["dataViewId", "username", "fullName", "email"]
        self.defaultColumnWidths = [40, 100, 200, 260]
        self.filterFields = ["username", "fullName", "email"]

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
        if col == 0:
            obj1 = int(userRecord1.dataViewId)
            obj2 = int(userRecord2.dataViewId)
        else:
            obj1 = userRecord1.GetValueForKey(self.columnKeys[col])
            obj2 = userRecord2.GetValueForKey(self.columnKeys[col])
        return Compare(obj1, obj2)

    @staticmethod
    def GetNumUserOrGroupFolders():
        """
        Get number of user or group folders.

        Fast method, ignoring filters.
        """
        dataDir = SETTINGS.general.dataDirectory
        userOrGroupFolderNames = os.walk(dataDir).next()[1]
        return len(userOrGroupFolderNames)

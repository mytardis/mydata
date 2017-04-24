"""
Represents the Groups tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
from ..utils import Compare
from .dataview import MyDataDataViewModel


class GroupsModel(MyDataDataViewModel):
    """
    Represents the Groups tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=arguments-differ
    def __init__(self):
        super(GroupsModel, self).__init__()
        self.columnNames = ["Id", "Short Name", "Full Name"]
        self.columnKeys = ["dataViewId", "shortName", "name"]
        self.defaultColumnWidths = [40, 200, 400]
        self.filterFields = ["name"]

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
        if col == 0:
            obj1 = int(groupRecord1.dataViewId)
            obj2 = int(groupRecord2.dataViewId)
        else:
            obj1 = groupRecord1.GetValueForKey(self.columnKeys[col])
            obj2 = groupRecord2.GetValueForKey(self.columnKeys[col])
        return Compare(obj1, obj2)

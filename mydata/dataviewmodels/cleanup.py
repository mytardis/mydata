import wx

from .dataview import MyDataDataViewModel
from .dataview import ColumnRenderer
from ..utils import Compare


class CleanupTab(MyDataDataViewModel):

    def __init__(self):
        super(CleanupTab, self).__init__()

        self.folderModel = None
        self.columnNames = ["Id", "Verified", "Select", "File"]
        self.columnKeys = ["dataViewId", "verifiedAt", "setDelete", "fileName"]
        self.defaultColumnWidths = [100, 200, 50, 700]
        self.filterFields = ["fileName"]

    def Compare(self, groupRecord1, groupRecord2, col, ascending):
        try:
            groupRecord1 = self.rowsData[self.GetRow(groupRecord1)]
            groupRecord2 = self.rowsData[self.GetRow(groupRecord2)]
        except TypeError:
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

    def GetColumnRenderer(self, col):
        if col == 2:
            renderer = ColumnRenderer.CHECKBOX
        else:
            renderer = ColumnRenderer.TEXT
        return renderer

    def SetValueByRow(self, val, row, col):
        setattr(self.rowsData[row], self.columnKeys[col], val)
        return True

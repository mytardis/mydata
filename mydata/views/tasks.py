"""
Represents the Tasks tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

import wx
import wx.dataview as dv


class TasksView(wx.Panel):
    """
    Represents the Tasks tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, parent, tasksModel):
        wx.Panel.__init__(self, parent, -1)

        self.tasksDataViewControl = dv.DataViewCtrl(self,
                                                    style=wx.BORDER_THEME |
                                                    dv.DV_ROW_LINES |
                                                    dv.DV_VERT_RULES |
                                                    dv.DV_MULTIPLE)

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if smallFont.GetPointSize() > 11:
            smallFont.SetPointSize(11)
        self.tasksDataViewControl.SetFont(smallFont)

        self.tasksModel = tasksModel

        self.tasksDataViewControl.AssociateModel(self.tasksModel)

        for col in range(1, self.tasksModel.GetColumnCount()):
            self.tasksDataViewControl\
                .AppendTextColumn(self.tasksModel.GetColumnName(col), col,
                                  width=self.tasksModel
                                  .GetDefaultColumnWidth(col),
                                  mode=dv.DATAVIEW_CELL_INERT)

        firstColumn = \
            self.tasksDataViewControl.PrependTextColumn("Id", 0, width=40)
        firstColumn.Alignment = wx.ALIGN_RIGHT
        firstColumn.Renderer.Alignment = wx.ALIGN_RIGHT
        firstColumn.MinWidth = 40

        for col in self.tasksDataViewControl.Columns:
            col.Sortable = True
            col.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        firstColumn.Reorderable = False

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.tasksDataViewControl, 1, wx.EXPAND)

    def GetTasksModel(self):
        """
        Returns the TasksModel instance associated with the view.
        """
        return self.tasksModel

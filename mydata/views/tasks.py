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

        c0 = self.tasksDataViewControl.PrependTextColumn("Id", 0, width=40)
        c0.Alignment = wx.ALIGN_RIGHT
        c0.Renderer.Alignment = wx.ALIGN_RIGHT
        c0.MinWidth = 40

        for c in self.tasksDataViewControl.Columns:
            c.Sortable = True
            c.Reorderable = True

        # Let's change our minds and not let the first col be moved.
        c0.Reorderable = False

        # set the Sizer property (same as SetSizer)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.tasksDataViewControl, 1, wx.EXPAND)

    def GetTasksModel(self):
        """
        Returns the TasksModel instance associated with the view.
        """
        return self.tasksModel

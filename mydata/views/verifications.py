"""
Represents the Verifications tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import wx
import wx.dataview as dv


class VerificationsView(wx.Panel):
    """
    Represents the Verifications tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    def __init__(self, parent, verificationsModel):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        # Create a dataview control
        self.verificationsDataViewControl = \
            dv.DataViewCtrl(self, style=wx.BORDER_THEME
                            | dv.DV_ROW_LINES
                            | dv.DV_VERT_RULES
                            | dv.DV_MULTIPLE)

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if smallFont.GetPointSize() > 11:
            smallFont.SetPointSize(11)
        self.verificationsDataViewControl.SetFont(smallFont)

        self.verificationsModel = verificationsModel

        self.verificationsDataViewControl.AssociateModel(
            self.verificationsModel)

        for col in range(0, self.verificationsModel.GetColumnCount()):
            self.verificationsDataViewControl\
                .AppendTextColumn(self.verificationsModel
                                  .GetColumnName(col),
                                  col,
                                  width=self.verificationsModel
                                  .GetDefaultColumnWidth(col),
                                  mode=dv.DATAVIEW_CELL_INERT)

        firstColumn = self.verificationsDataViewControl.Columns[0]
        firstColumn.Alignment = wx.ALIGN_RIGHT
        firstColumn.Renderer.Alignment = wx.ALIGN_RIGHT
        firstColumn.MinWidth = 40

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(self.verificationsDataViewControl, 1, wx.EXPAND)

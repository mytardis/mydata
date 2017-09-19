"""
The VerificationsDataView class extends the MyDataDataView class, providing
additional functionality for the verifications (datafile look-ups) view,
including information about the cache hit rate.
"""
import wx

from ..dataviewmodels.dataview import DATAVIEW_MODELS
from .dataview import MyDataDataView


class VerificationsDataView(MyDataDataView):
    """
    The VerificationsDataView class extends the MyDataDataView class, providing
    additional functionality for the verifications (datafile look-ups) view,
    including information about the cache hit rate.
    """
    def __init__(self, parent):
        super(VerificationsDataView, self).__init__(parent, 'verifications')

        sizer = self.GetSizer()

        self.footerPanel = wx.Panel(self)

        # TO DO: Small font should be defined in utils or wherever:
        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if smallFont.GetPointSize() > 11:
            smallFont.SetPointSize(11)

        self.cacheHitSummary = wx.StaticText(self.footerPanel)
        self.cacheHitSummary.SetFont(smallFont)
        sizer.Add(self.footerPanel, 0, wx.EXPAND)
        self.Fit()

        self.updateCacheHitSummaryTimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.UpdateCacheHitSummary,
                  self.updateCacheHitSummaryTimer)

    def UpdateCacheHitSummary(self, event):
        """
        Update the cache hit summary.
        """
        hits = DATAVIEW_MODELS['verifications'].GetFoundInCacheCount()
        total = DATAVIEW_MODELS['verifications'].GetCount() + hits
        self.cacheHitSummary.SetLabel(
            "%s of %s datafile lookups found in cache." % (hits, total))
        if event:
            event.Skip()

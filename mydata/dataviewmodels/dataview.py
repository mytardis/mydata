"""
MyData classes can import DataViewIndexListModel from here, and automatically
get the right the module, which depends on the wxPython version.
"""
# pylint: disable=unused-import
import traceback

import wx
if wx.version().startswith("3.0.3.dev"):
    from wx.dataview import DataViewIndexListModel  # pylint: disable=no-name-in-module
else:
    from wx.dataview import PyDataViewIndexListModel as DataViewIndexListModel

from ..logs import logger  # pylint: disable=wrong-import-position


def TryRowValueChanged(dataViewModel, row, col):
    """
    Notify views of a change in value
    """
    try:
        if row < dataViewModel.GetCount():
            dataViewModel.RowValueChanged(row, col)
        else:
            logger.warning("TryRowValueChanged called with "
                           "row=%d, dataViewModel.GetRowCount()=%d" %
                           (row, dataViewModel.GetRowCount()))
            dataViewModel.RowValueChanged(row, col)
    except wx.PyAssertionError:
        logger.warning(traceback.format_exc())

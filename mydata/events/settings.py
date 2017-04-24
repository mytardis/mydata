"""
mydata/events/settings.py

This module contains event handlers relating to settings.
"""
import wx

from ..dataviewmodels.dataview import DATAVIEW_MODELS
from ..logs import logger
from ..views.settings import SettingsDialog
from ..settings import SETTINGS


def OnSettings(event, validationMessage=None):
    """
    Open the Settings dialog, which could be in response to the main
    toolbar's Refresh icon, or in response to in response to the task bar
    icon's "MyData Settings" menu item, or in response to MyData being
    launched without any previously saved settings.
    """
    # When Settings is launched by user e.g. from the toolbar, we don't
    # want it to be aborted, so we'll ensure FLAGS.shouldAbort is False.
    app = wx.GetApp()
    if event:
        app.ResetShouldAbortStatus()
    app.frame.SetStatusMessage("")
    settingsDialog = SettingsDialog(app.frame,
                                    size=wx.Size(400, 400),
                                    style=wx.DEFAULT_DIALOG_STYLE,
                                    validationMessage=validationMessage)
    if settingsDialog.ShowModal() == wx.ID_OK:
        logger.debug("settingsDialog.ShowModal() returned wx.ID_OK")
        app.frame.SetTitle("MyData - " + SETTINGS.general.instrumentName)
        DATAVIEW_MODELS['tasks'].DeleteAllRows()
        app.scheduleController.ApplySchedule(event)

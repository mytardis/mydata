"""
mydata/events/stop.py

This module contains methods relating to stopping MyData's scan-and-upload
processes.
"""
import os
import wx

from ..threads.flags import FLAGS
from ..utils import BeginBusyCursorIfRequired
from ..utils import EndBusyCursorIfRequired

from ..logs import logger


def CheckIfShouldAbort():
    """
    Check if user has requested aborting scans and uploads,
    and if so, restores icons and cursors to their default state,
    and then raises an exception.
    """
    if 'MYDATA_TESTING' in os.environ:
        return FLAGS.shouldAbort
    app = wx.GetApp()
    if FLAGS.shouldAbort or app.foldersController.canceled:
        RestoreUserInterfaceForAbort()
        return True
    return False


def RestoreUserInterfaceForAbort():
    """
    Restores icons and cursors to their default state.
    """
    app = wx.GetApp()
    wx.CallAfter(EndBusyCursorIfRequired)
    wx.CallAfter(app.frame.toolbar.EnableTestAndUploadToolbarButtons)
    if app.testRunFrame.IsShown():
        wx.CallAfter(app.testRunFrame.Hide)
    FLAGS.scanningFolders = False
    FLAGS.testRunRunning = False


def ResetShouldAbortStatus():
    """
    Resets the ShouldAbort status
    """
    app = wx.GetApp()
    FLAGS.shouldAbort = False
    app.foldersController.ClearStatusFlags()


def OnStop(event):
    """
    The user pressed the stop button on the main toolbar.
    """
    from . import PostEvent
    app = wx.GetApp()
    FLAGS.shouldAbort = True
    if app.foldersController.started:
        BeginBusyCursorIfRequired()
        PostEvent(app.foldersController.ShutdownUploadsEvent(canceled=True))
    else:
        RestoreUserInterfaceForAbort()
        message = "Data scans and uploads were canceled."
        logger.info(message)
        app.frame.SetStatusMessage(message)
    if event:
        event.Skip()
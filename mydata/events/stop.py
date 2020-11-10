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
from ..utils.exceptions import UserAborted

from ..logs import logger


def CheckIfShouldAbort():
    """
    Check if user has requested aborting scans and uploads,
    and if so, restores icons and cursors to their default state,
    and then raises an exception.
    """
    if 'MYDATA_TESTING' in os.environ:
        return FLAGS.shouldAbort
    if FLAGS.shouldAbort:
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
    # FLAGS.shouldAbort = False
    # if hasattr(app, "foldersController"):
    #     app.foldersController.canceled = False



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
    from . import MYDATA_EVENTS
    from . import PostEvent
    app = wx.GetApp()
    FLAGS.shouldAbort = True
    if app.foldersController.started:
        BeginBusyCursorIfRequired()
        PostEvent(MYDATA_EVENTS.ShutdownUploadsEvent(canceled=True))
    else:
        RestoreUserInterfaceForAbort()
        message = "Data scans and uploads were canceled."
        logger.info(message)
        app.frame.SetStatusMessage(message)
    if event:
        event.Skip()


def ShouldCancelUpload(uploadModel):
    """
    Return True if the upload should be canceled
    """
    app = wx.GetApp()
    if hasattr(app, "foldersController"):
        return app.foldersController.canceled or uploadModel.canceled

    # This code would only run in tests where a scheduled progress query
    # from one test attempts to run in a subsequent test, but the subsequent
    # test doesn't create a folders controller instance.  (See the use of
    # threading.Timer in mydata.utils.progress.)
    return True


def RaiseExceptionIfUserAborted(setStatusMessage=None):
    """
    Check if user has aborted by clicking the Stop button on the main
    MyData frame's toolbar.  And if so, raise UserAborted.

    A function accepting a status message string argument can be
    supplied which will be called before the exception is raised.
    """
    app = wx.GetApp()
    if hasattr(app, "ShouldAbort") and app.ShouldAbort():
        message = "Canceled by user"
        if setStatusMessage:
            setStatusMessage(message)
        raise UserAborted(message)

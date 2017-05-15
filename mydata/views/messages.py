"""
Methods for displaying messages
"""
import os
import sys

import wx

from ..logs import logger
from ..threads.flags import FLAGS
from ..threads.locks import LOCKS
from ..utils import BeginBusyCursorIfRequired

LAST_ERROR_MESSAGE = None
LAST_CONFIRMATION_QUESTION = None


def ShowMessageDialog(event):
    """
    Display a message dialog.

    Sometimes multiple threads can encounter the same exception
    at around the same time.  The first thread's exception leads
    to a modal error dialog, which blocks the events queue, so
    the next thread's (identical) show message dialog event doesn't
    get caught until after the first message dialog has been closed.
    In this case, we check if we already showed an error dialog with
    the same message.
    """
    if FLAGS.showingErrorDialog:
        logger.debug("Refusing to show message dialog for message "
                     "\"%s\" because we are already showing an error "
                     "dialog." % event.message)
        return
    elif FLAGS.showingConfirmationDialog:
        logger.debug("Refusing to show message dialog for message "
                     "\"%s\" because we are already showing a confirmation "
                     "dialog." % event.message)
        return
    elif event.message == LAST_ERROR_MESSAGE:
        logger.debug("Refusing to show message dialog for message "
                     "\"%s\" because we already showed an error "
                     "dialog with the same message." % event.message)
        return
    with LOCKS.updateLastErrorMessage:
        globals()['LAST_ERROR_MESSAGE'] = event.message
    if event.icon == wx.ICON_ERROR:
        FLAGS.showingErrorDialog = True
    dlg = wx.MessageDialog(None, event.message, event.title,
                           wx.OK | event.icon)
    try:
        wx.EndBusyCursor()
        needToRestartBusyCursor = True
    except:
        needToRestartBusyCursor = False
    if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ:
        dlg.ShowModal()
    else:
        sys.stderr.write("%s\n" % event.message)
    app = wx.GetApp()
    if needToRestartBusyCursor and not app.foldersController.IsShuttingDown() \
            and FLAGS.performingLookupsAndUploads:
        BeginBusyCursorIfRequired()
    if event.icon == wx.ICON_ERROR:
        FLAGS.showingErrorDialog = False


def ShowConfirmationDialog(event):
    """
    Display a confirmation (Yes/No) dialog.

    The current use case is that MyData detects that the scp_username and/or
    scp_hostname attributes are missing from the assigned storage box, so it
    shuts down the upload threads (with failed=True) and asks the user if
    they would like to assume that the storage box location is accessible
    locally (i.e. we can copy data to a local directory or mount point
    instead of using SCP).
    """
    if FLAGS.showingErrorDialog:
        logger.debug("Refusing to show confirmation dialog for question "
                     "\"%s\" because we are already showing a confirmation "
                     "dialog." % event.question)
        return
    elif FLAGS.showingConfirmationDialog:
        logger.debug("Refusing to show confirmation dialog for question "
                     "\"%s\" because we are already showing a confirmation "
                     "dialog." % event.question)
        return
    elif event.question == LAST_CONFIRMATION_QUESTION:
        logger.debug("Refusing to show confirmation dialog for question "
                     "\"%s\" because we already showed a confirmation "
                     "dialog with the same question." % event.question)
        return
    with LOCKS.updateLastConfirmationQuestion:
        globals()['LAST_CONFIRMATION_QUESTION'] = event.question
    FLAGS.showingConfirmationDialog = True
    dlg = wx.MessageDialog(
        None, event.question, event.title, wx.YES | wx.NO | wx.ICON_QUESTION)
    if 'MYDATA_DONT_SHOW_MODAL_DIALOGS' not in os.environ:
        result = dlg.ShowModal()
    else:
        sys.stderr.write("%s\n" % event.question)
        result = wx.ID_LOWEST  # Anything except for wx.ID_YES and wx.ID_NO
    FLAGS.showingConfirmationDialog = False

    if result == wx.ID_YES:
        if hasattr(event, "onYes"):
            event.onYes()
        else:
            logger.warning("Confirmation dialog has no event handler for Yes")
    elif result == wx.ID_NO and hasattr(event, "onNo"):
        if hasattr(event, "onNo"):
            event.onNo()
        else:
            logger.warning("Confirmation dialog has no event handler for No")

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


def ResetDialogSemaphores():
    """
    Reset dialog semaphores, so new dialogs can be displayed without them
    being vetoed because MyData thinks a dialog is already being displayed.
    """
    FLAGS.showingErrorDialog = False
    FLAGS.showingConfirmationDialog = False

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
    if FLAGS.showingConfirmationDialog:
        logger.debug("Refusing to show message dialog for message "
                     "\"%s\" because we are already showing a confirmation "
                     "dialog." % event.message)
        return
    if event.message == LAST_ERROR_MESSAGE:
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
        ResetDialogSemaphores()

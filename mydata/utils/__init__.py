"""
Miscellaneous utility functions.
"""
import webbrowser

import psutil
import requests
import wx

from mydata.logs import logger


def PidIsRunning(pid):
    """
    Check if a process with PID pid is running.
    """
    try:
        proc = psutil.Process(int(pid))
        if proc.status == psutil.STATUS_DEAD:
            return False
        if proc.status == psutil.STATUS_ZOMBIE:
            return False
        return True  # Assume other status are valid
    except psutil.NoSuchProcess:
        return False


def HumanReadableSizeString(num):
    """
    Returns human-readable string.
    """
    for unit in ['bytes', 'KB', 'MB', 'GB']:
        if -1024.0 < num < 1024.0:
            return "%3.1f %s" % (num, unit)
        num /= 1024.0
    return "%3.1f %s" % (num, 'TB')


def UnderscoreToCamelcase(value):
    """
    Convert underscore_separated to camelCase.
    """
    output = ""
    firstWordPassed = False
    for word in value.split("_"):
        if not word:
            output += "_"
            continue
        if firstWordPassed:
            output += word.capitalize()
        else:
            output += word.lower()
        firstWordPassed = True
    return output


def BytesToHuman(numBytes):
    """
    Returns human-readable string.
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for index, symbol in enumerate(symbols):
        prefix[symbol] = 1 << (index + 1) * 10
    for symbol in reversed(symbols):
        if numBytes >= prefix[symbol]:
            value = float(numBytes) / prefix[symbol]
            return '%.1f%s' % (value, symbol)
    return "%sB" % numBytes


def BeginBusyCursorIfRequired():
    """
    Begin busy cursor if it's not already being displayed.
    """
    try:
        if not wx.IsBusy():
            wx.BeginBusyCursor()
    except wx.PyAssertionError, err:
        logger.warning(err)


def EndBusyCursorIfRequired(event=None):
    """
    The built in wx.EndBusyCursor raises an ugly exception if the
    busy cursor has already been stopped.
    """
    try:
        wx.EndBusyCursor()
        if event and hasattr(event, 'settingsDialog') and event.settingsDialog:
            if wx.version().startswith("3.0.3.dev"):
                arrowCursor = wx.Cursor(wx.CURSOR_ARROW)
            else:
                arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
            event.settingsDialog.dialogPanel.SetCursor(arrowCursor)
    except wx.PyAssertionError, err:
        if "no matching wxBeginBusyCursor()" \
                not in str(err):
            logger.warning(str(err))
            raise

def OpenUrl(url, new=0, autoraise=True):
    """
    Open URL in web browser or just check URL is accessible if running tests.
    """
    if wx.PyApp.IsMainLoopRunning():
        webbrowser.open(url, new, autoraise)
    else:
        response = requests.get('http://www.example.com')
        assert response.status_code == 200

"""
Miscellaneous utility functions.
"""

import psutil
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
        if num < 1024.0 and num > -1024.0:
            return "%3.0f %s" % (num, unit)
        num /= 1024.0
    return "%3.0f %s" % (num, 'TB')


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


class ConnectionStatus(object):
    """
    Enumerated data type
    """
    # pylint: disable=invalid-name
    # pylint: disable=too-few-public-methods
    CONNECTED = 0
    DISCONNECTED = 1


def BeginBusyCursorIfRequired():
    """
    Begin busy cursor if it's not already being displayed.
    """
    if not wx.IsBusy():
        wx.BeginBusyCursor()


def EndBusyCursorIfRequired():
    """
    The built in wx.EndBusyCursor raises an ugly exception if the
    busy cursor has already been stopped.
    """
    # pylint: disable=no-member
    # Otherwise pylint complains about PyAssertionError.
    # pylint: disable=protected-access
    try:
        wx.EndBusyCursor()
    except wx._core.PyAssertionError, err:
        if "no matching wxBeginBusyCursor()" \
                not in str(err):
            logger.error(str(err))
            raise

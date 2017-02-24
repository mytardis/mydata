# -*- coding: utf-8 -*-
"""
Miscellaneous utility functions.
"""
import unicodedata
import sys

import psutil
import wx

from ..logs import logger


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


def BeginBusyCursorIfRequired(event=None):
    """
    Begin busy cursor if it's not already being displayed.
    """
    try:
        if not wx.IsBusy():
            wx.BeginBusyCursor()
        if event and hasattr(event, 'settingsDialog') and event.settingsDialog:
            if wx.version().startswith("3.0.3.dev"):
                busyCursor = wx.Cursor(wx.CURSOR_WAIT)
            else:
                busyCursor = wx.StockCursor(wx.CURSOR_WAIT)
            event.settingsDialog.dialogPanel.SetCursor(busyCursor)
    except wx.PyAssertionError as err:
        logger.warning(err)


def EndBusyCursorIfRequired(event=None):
    """
    The built in wx.EndBusyCursor raises an ugly exception if the
    busy cursor has already been stopped.
    """
    try:
        if wx.IsBusy():
            wx.EndBusyCursor()
        if event and hasattr(event, 'settingsDialog') and event.settingsDialog:
            if wx.version().startswith("3.0.3.dev"):
                arrowCursor = wx.Cursor(wx.CURSOR_ARROW)
            else:
                arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
            event.settingsDialog.dialogPanel.SetCursor(arrowCursor)
    except wx.PyAssertionError as err:
        if "no matching wxBeginBusyCursor()" \
                not in str(err):
            logger.warning(str(err))
            raise


def SafeStr(err, inputEnc=sys.getfilesystemencoding(), outputEnc='utf-8'):
    # pylint: disable=anomalous-unicode-escape-in-string
    """
    Safely return a string representation of an exception, possibly including
    a user-defined filesystem path.

    For an exception like this:

        except Exception as err:

    we can use str(err) to get a string representation of the error for
    logging (or for displaying in a message dialog).

    However in Python 2, Exception.__str__ can raise UnicodeDecodeError
    if the exception contains non-ASCII characters.  In MyData, these
    non-ASCII characters generally come from file or folder names which
    MyData is scanning, so they are expected to be encoded using
    sys.getfilesystemencoding().

    Given that str(err) can raise UnicodeDecodeError, we could use
    err.message, but it has been deprecated in some versions of Python 2
    and has been removed in Python 3.  In most cases, it can be replaced
    by err.args[0].  However in the case of IOError, the string
    representation is a combination of the args, e.g.

      "IOError: [Errno 5] foo: 'bar'"

    for IOError(5, "foo", "bar").

    SafeStr's default output encoding is utf-8, and before being encoded
    as utf-8, the Unicode string is normalized.  For example, suppose a
    filename contains the letter 'e' with an acute accent (é).  This could
    be represented by a single Unicode code point: u'\u00E9', or as the
    letter 'e' followed by the "combining acute accent", i.e. u'e\u0301'.
    We can normalize these as follows:

    >>> import unicodedata
    >>> unicodedata.normalize('NFC', u'\u00E9')
    u'\xe9'
    >>> unicodedata.normalize('NFC', u'e\u0301')
    u'\xe9'
    >>> u'\xe9' == u'\u00E9'
    True

    """
    try:
        return str(err)
    except UnicodeDecodeError:
        inputEnc = inputEnc or 'utf-8'
        if isinstance(err, IOError) or isinstance(err, OSError):
            decoded = "%s: [Errno %s] %s: '%s'" \
                % (type(err).__name__, err.errno,
                   err.strerror.decode(inputEnc),
                   err.filename.decode(inputEnc))
        else:
            decoded = err.args[0].decode(inputEnc)
    normalized = unicodedata.normalize('NFC', decoded)
    return normalized.encode(outputEnc)


def Compare(obj1, obj2):
    """
    Compare the two objects obj1 and obj2 and return an integer according
    to the outcome. The return value is negative if obj1 < obj2, zero if
    obj1 == obj2 and strictly positive if obj1 > obj2.
    """
    return (obj1 > obj2) - (obj1 < obj2)

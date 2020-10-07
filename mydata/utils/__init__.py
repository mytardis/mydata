# -*- coding: utf-8 -*-
"""
Miscellaneous utility functions.
"""
import os
import sys
import subprocess
import traceback
import unicodedata
import webbrowser

import appdirs
import psutil
import wx

from ..constants import APPNAME, APPAUTHOR
from ..logs import logger
from ..threads.locks import LOCKS


def PidIsRunning(pid):
    """
    Check if a process with PID pid is running.
    """
    try:
        proc = psutil.Process(int(pid))
        if proc.status() == psutil.STATUS_DEAD:
            return False
        if proc.status() == psutil.STATUS_ZOMBIE:
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


def BeginBusyCursorIfRequired(settingsDialog=None):
    """
    Begin busy cursor if it's not already being displayed.
    """
    try:
        if not wx.IsBusy():
            wx.BeginBusyCursor()
        if settingsDialog:
            if 'phoenix' in wx.PlatformInfo:
                busyCursor = wx.Cursor(wx.CURSOR_WAIT)
            else:
                busyCursor = wx.StockCursor(wx.CURSOR_WAIT)
            settingsDialog.dialogPanel.SetCursor(busyCursor)
    except wx.wxAssertionError as err:
        logger.warning(err)


def EndBusyCursorIfRequired(settingsDialog=None):
    """
    The built in wx.EndBusyCursor raises an ugly exception if the
    busy cursor has already been stopped.
    """
    try:
        if wx.IsBusy():
            wx.EndBusyCursor()
        if settingsDialog:
            if 'phoenix' in wx.PlatformInfo:
                arrowCursor = wx.Cursor(wx.CURSOR_ARROW)
            else:
                arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
            settingsDialog.dialogPanel.SetCursor(arrowCursor)
    except wx.wxAssertionError as err:
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
        if isinstance(err, (IOError, OSError)):
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


def HandleGenericErrorWithDialog(err):
    """
    Handle an exception where the user should be notified in a dialog.

    Designed to be called from a worker thread, this method uses
    wx.CallAfter to display the error message from the main thread.
    """
    logger.error(traceback.format_exc())
    if type(err).__name__ == "WindowsError" and \
            "The handle is invalid" in str(err):
        message = "An error occurred, suggesting " \
            "that you have launched MyData.exe from a " \
            "Command Prompt window.  Please launch it " \
            "from a shortcut or from a Windows Explorer " \
            "window instead.\n" \
            "\n" \
            "See: https://bugs.python.org/issue3905"
        wx.CallAfter(DisplayError, message)
    else:
        raise err


def OpenUrl(url, new=0, autoraise=True):
    """
    Open URL in web browser or just check URL is accessible if running tests.
    """
    webbrowser.open(url, new, autoraise)


def CreateConfigPathIfNecessary():
    """
    Create path for saving MyData.cfg if it doesn't already exist.
    """
    if sys.platform.startswith("win"):
        # We use a setup wizard on Windows which runs with admin
        # privileges, so we can ensure that the appdirPath below,
        # i.e. C:\ProgramData\Monash University\MyData\ is
        # writeable by all users.
        appdirPath = appdirs.site_config_dir(APPNAME, APPAUTHOR)
    else:
        # On Mac, we currently use a DMG drag-and-drop installation, so
        # we can't create a system-wide MyData.cfg writeable by all users.
        appdirPath = appdirs.user_data_dir(APPNAME, APPAUTHOR)
    if not os.path.exists(appdirPath):
        os.makedirs(appdirPath)
    return appdirPath


def InitializeTrustedCertsPath():
    """
    Tell the requests module where to find the CA (Certificate Authority)
    certificates bundled with MyData.
    """
    if hasattr(sys, "frozen"):
        if sys.platform.startswith("darwin"):
            certPath = os.path.realpath(os.path.join(
                os.path.dirname(sys.executable), '..', 'Resources'))
        else:
            certPath = os.path.dirname(sys.executable)
        os.environ['REQUESTS_CA_BUNDLE'] = \
            os.path.join(certPath, 'cacert.pem')


def GnomeShellIsRunning():
    """
    Check if the GNOME Shell desktop environment is running.
    Helper function for CheckIfSystemTrayFunctionalityMissing.
    """
    for pid in psutil.pids():
        try:
            proc = psutil.Process(pid)
            if 'gnome-shell' in proc.name():
                return True
        except psutil.NoSuchProcess:
            pass
    return False


def CheckIfSystemTrayFunctionalityMissing():
    """
    Recent Linux desktop envrionments have removed the system tray icon
    functionality and replaced it with an indicator panel.  wxPython doesn't
    yet support using inidicator panels, so on Ubuntu, we check if the
    indicator-systemtray-unity package (which restores the system tray icon
    functionality) is installed.
    """
    if os.getenv('DESKTOP_SESSION', '') == 'ubuntu':
        proc = subprocess.Popen(['dpkg', '-s',
                                 'indicator-systemtray-unity'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        _ = proc.communicate()
        if proc.returncode != 0:
            message = "Running MyData on Ubuntu's default " \
                "(Unity) desktop requires the " \
                "indicator-systemtray-unity package: " \
                "https://github.com/GGleb/" \
                "indicator-systemtray-unity"
            DisplayError(message)
            sys.exit(1)
    elif GnomeShellIsRunning():
        # We are running GNOME Shell which has removed the
        # system tray funcionality found in GNOME v2.
        # For now, we'll assume a RHEL / CentOS system with rpm:
        proc = subprocess.Popen(['rpm', '-q',
                                 'gnome-shell-extension-top-icons'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        _ = proc.communicate()
        if proc.returncode != 0:
            message = "Running MyData in GNOME Shell " \
                "requires the gnome-shell-extension-top-icons package."
            DisplayError(message)
            sys.exit(1)
        proc = subprocess.Popen(
            ['gsettings', 'get', 'org.gnome.shell', 'enabled-extensions'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, _ = proc.communicate()
        if b'top-icons' not in stdout:
            sys.stderr.write("Enabling the TopIcons GNOME shell extension\n")
            proc = subprocess.Popen(
                ['gnome-shell-extension-tool', '-e',
                 'top-icons@gnome-shell-extensions.gcampax.github.com'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            _ = proc.communicate()
            if proc.returncode != 0:
                message = "Failed to enable the TopIcons GNOME shell extension."
                DisplayError(message)
                sys.exit(1)
    else:
        logger.info(
            "Assuming desktop environment supports system tray icons.\n")


def DisplayError(message):
    """
    Display a modal error dialog
    """
    if LOCKS.displayModalDialog.acquire(False):
        wx.MessageBox(message, APPNAME, wx.ICON_ERROR)
        LOCKS.displayModalDialog.release()
    else:
        sys.stderr.write("%s\n" % message)


def MyDataInstallLocation():
    """
    Return MyData install location
    """
    if hasattr(sys, 'frozen'):
        return os.path.dirname(sys.executable)
    try:
        return os.path.realpath(
            os.path.join(os.path.dirname(__file__), "..", ".."))
    except:
        return os.getcwd()

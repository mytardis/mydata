"""
Ensure that MyData starts automatically when the user logs in if
the "Start Automatically" checkbox is ticked in the Advanced tab
of the Settings dialog.
"""
import getpass
import os
import subprocess
import shutil
import sys
import tempfile
import traceback

import psutil

from ..logs import logger
from ..subprocesses import DEFAULT_STARTUP_INFO
from ..subprocesses import DEFAULT_CREATION_FLAGS


def UpdateAutostartFile(settingsModel):
    """
    Ensure that MyData starts automatically when the user logs in if
    the "Start Automatically" checkbox is ticked in the Advanced tab
    of the Settings dialog.
    """
    if sys.platform.startswith("win"):
        UpdateWindowsAutostartFile(settingsModel)
    elif sys.platform.startswith("darwin"):
        UpdateMacAutostartFile(settingsModel)
    elif sys.platform.startswith("linux") and hasattr(sys, "frozen"):
        UpdateLinuxAutostartFile(settingsModel)


def IsMyDataShortcutInWinStartupItems(allUsers=False):
    """
    Check for MyData shortcut(s) in Winodows startup folder(s).
    """
    with tempfile.NamedTemporaryFile(suffix='.vbs', delete=False) \
            as vbScript:
        script = r"""
set objShell = CreateObject("WScript.Shell")
startupFolder = objShell.SpecialFolders("Startup")
path = startupFolder & "\" & "MyData.lnk"

Set fso = CreateObject("Scripting.FileSystemObject")
If (fso.FileExists(path)) Then
msg = path & " exists."
Wscript.Echo(msg)
Wscript.Quit(0)
Else
msg = path & " doesn't exist."
Wscript.Echo(msg)
Wscript.Quit(1)
End If
        """
        if allUsers:
            script = script.replace("Startup", "AllUsersStartup")
        vbScript.write(script)
    cmdList = ['cscript', '//Nologo', vbScript.name]
    logger.info("Checking for MyData shortcut in %s "
                "startup items." % "common" if allUsers else "user")
    proc = subprocess.Popen(cmdList, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, shell=False,
                            startupinfo=DEFAULT_STARTUP_INFO,
                            creationflags=DEFAULT_CREATION_FLAGS)
    proc.communicate()
    shortcutInStartupItems = (proc.returncode == 0)
    try:
        os.unlink(vbScript.name)
    except:
        logger.error(traceback.format_exc())
    return shortcutInStartupItems


def AddMyDataToWinStartupFolder():
    """
    Add MyData shortcut to Windows startup folder.
    """
    logger.info("Adding MyData shortcut to startup items.")
    pathToMyDataExe = \
        r"C:\Program Files (x86)\MyData\MyData.exe"
    if hasattr(sys, "frozen"):
        pathToMyDataExe = os.path.realpath(r'.\MyData.exe')
    with tempfile.NamedTemporaryFile(suffix='.vbs',
                                     delete=False) as vbScript:
        script = r"""
Set oWS = WScript.CreateObject("WScript.Shell")
startupFolder = oWS.SpecialFolders("Startup")
sLinkFile = startupFolder & "\" & "MyData.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "%s"
oLink.Save
        """ % pathToMyDataExe
        vbScript.write(script)
    cmdList = ['cscript', '//Nologo', vbScript.name]
    logger.info("Adding MyData shortcut to user "
                "startup items.")
    proc = subprocess.Popen(cmdList, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=False,
                            startupinfo=DEFAULT_STARTUP_INFO,
                            creationflags=DEFAULT_CREATION_FLAGS)
    output, _ = proc.communicate()
    success = (proc.returncode == 0)
    if not success:
        logger.error(output)
    try:
        os.unlink(vbScript.name)
    except:
        logger.error(traceback.format_exc())


def RemoveMyDataFromWinStartupFolder():
    """
    Remove MyData shortcut from Windows startup folder.
    """
    logger.info("Removing MyData from Win startup folder.")
    with tempfile.NamedTemporaryFile(suffix='.vbs',
                                     delete=False) as vbScript:
        script = r"""
Set oWS = WScript.CreateObject("WScript.Shell")
Set oFS = CreateObject("Scripting.FileSystemObject")
startupFolder = oWS.SpecialFolders("Startup")
sLinkFile = startupFolder & "\" & "MyData.lnk"
oFS.DeleteFile sLinkFile
        """
        vbScript.write(script)
    cmdList = ['cscript', '//Nologo', vbScript.name]
    proc = subprocess.Popen(cmdList, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=False,
                            startupinfo=DEFAULT_STARTUP_INFO,
                            creationflags=DEFAULT_CREATION_FLAGS)
    output, _ = proc.communicate()
    success = (proc.returncode == 0)
    if not success:
        logger.error(output)
    try:
        os.unlink(vbScript.name)
    except:
        logger.error(traceback.format_exc())


def UpdateWindowsAutostartFile(settingsModel):
    """
    Ensure that MyData starts automatically on Windows when the user
    logs in if the "Start Automatically" checkbox is ticked in the
    Advanced tab of the Settings dialog.
    """
    shortcutInStartupItems = IsMyDataShortcutInWinStartupItems(allUsers=False)
    if shortcutInStartupItems:
        logger.info("Found MyData shortcut in user startup items.")
    else:
        logger.info("Didn't find MyData shortcut in user "
                    "startup items.")
    shortcutInCommonStartupItems = \
        IsMyDataShortcutInWinStartupItems(allUsers=True)
    if shortcutInCommonStartupItems:
        logger.info("Found MyData shortcut in common startup items.")
    else:
        logger.info("Didn't find MyData shortcut in common startup items.")
    if (shortcutInStartupItems or shortcutInCommonStartupItems) \
            and settingsModel.advanced.startAutomaticallyOnLogin:
        logger.debug("MyData is already set to start automatically "
                     "on login.")
    elif (not shortcutInStartupItems and
          not shortcutInCommonStartupItems) and \
            settingsModel.advanced.startAutomaticallyOnLogin:
        AddMyDataToWinStartupFolder()
    elif (shortcutInStartupItems or
          shortcutInCommonStartupItems) and \
            not settingsModel.advanced.startAutomaticallyOnLogin:
        RemoveMyDataFromWinStartupFolder()


def UpdateMacAutostartFile(settingsModel):
    """
    Ensure that MyData starts automatically on macOS when the user
    logs in if the "Start Automatically" checkbox is ticked in the
    Advanced tab of the Settings dialog.
    """
    # Update ~/Library/Preferences/com.apple.loginitems.plist
    # cfprefsd can cause unwanted caching.
    # It will automatically respawn when needed.
    for proc in psutil.process_iter():
        if proc.name() == "cfprefsd" and \
                proc.username() == getpass.getuser():
            proc.kill()
    applescript = \
        'tell application "System Events" ' \
        'to get the name of every login item'
    cmdString = "osascript -e '%s'" % applescript
    loginItemsString = subprocess.check_output(cmdString,
                                               shell=True)
    loginItems = [item.strip() for item in
                  loginItemsString.split(',')]
    if 'MyData' in loginItems and settingsModel.advanced.startAutomaticallyOnLogin:
        logger.debug("MyData is already set to start automatically "
                     "on login.")
    elif 'MyData' not in loginItems and \
            settingsModel.advanced.startAutomaticallyOnLogin:
        logger.info("Adding MyData to login items.")
        pathToMyDataApp = "/Applications/MyData.app"
        if hasattr(sys, "frozen"):
            # Working directory in py2app bundle is
            # MyData.app/Contents/Resources/
            pathToMyDataApp = os.path.realpath('../..')
        applescript = \
            'tell application "System Events" ' \
            'to make login item at end with properties ' \
            '{path:"%s", hidden:false}' % pathToMyDataApp
        cmdString = "osascript -e '%s'" % applescript
        exitCode = subprocess.call(cmdString, shell=True)
        if exitCode != 0:
            logger.error("Received exit code %d from %s"
                         % (exitCode, cmdString))
    elif 'MyData' in loginItems and \
            not settingsModel.advanced.startAutomaticallyOnLogin:
        logger.info("Removing MyData from login items.")
        applescript = \
            'tell application "System Events" to ' \
            'delete login item "MyData"'
        cmdString = "osascript -e '%s'" % applescript
        exitCode = subprocess.call(cmdString, shell=True)
        if exitCode != 0:
            logger.error("Received exit code %d from %s"
                         % (exitCode, cmdString))


def UpdateLinuxAutostartFile(settingsModel):
    """
    Ensure that MyData starts automatically on Linux when the user
    logs in if the "Start Automatically" checkbox is ticked in the
    Advanced tab of the Settings dialog.
    """
    autostartDir = os.path.join(os.path.expanduser('~'),
                                ".config", "autostart")
    if settingsModel.advanced.startAutomaticallyOnLogin:
        if not os.path.exists(autostartDir):
            os.makedirs(autostartDir)
        pathToMyDataDesktop = \
            os.path.join(os.path.dirname(sys.executable),
                         "MyData.desktop")
        shutil.copy(pathToMyDataDesktop, autostartDir)
    else:
        mydataAutostartPath = os.path.join(autostartDir,
                                           "MyData.desktop")
        if os.path.exists(mydataAutostartPath):
            os.remove(mydataAutostartPath)

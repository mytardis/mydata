"""
Ensure that MyData starts automatically when the user logs in if
the "Start Automatically" checkbox is ticked in the Advanced tab
of the Settings dialog.
"""
import os
import subprocess
import shutil
import sys
import tempfile
import traceback

from ..logs import logger
from ..settings import SETTINGS
from ..subprocesses import DEFAULT_STARTUP_INFO
from ..subprocesses import DEFAULT_CREATION_FLAGS


def UpdateAutostartFile():
    """
    Ensure that MyData starts automatically when the user logs in if
    the "Start Automatically" checkbox is ticked in the Advanced tab
    of the Settings dialog.
    """
    if sys.platform.startswith("win"):
        UpdateWindowsAutostartFile()
    elif sys.platform.startswith("darwin"):
        UpdateMacAutostartFile()
    elif sys.platform.startswith("linux") and hasattr(sys, "frozen"):
        UpdateLinuxAutostartFile()


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


def UpdateWindowsAutostartFile():
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
            and SETTINGS.advanced.startAutomaticallyOnLogin:
        logger.debug("MyData is already set to start automatically "
                     "on login.")
    elif (not shortcutInStartupItems and
          not shortcutInCommonStartupItems) and \
            SETTINGS.advanced.startAutomaticallyOnLogin:
        AddMyDataToWinStartupFolder()
    elif (shortcutInStartupItems or
          shortcutInCommonStartupItems) and \
            not SETTINGS.advanced.startAutomaticallyOnLogin:
        RemoveMyDataFromWinStartupFolder()


def UpdateMacAutostartFile():
    """
    Ensure that MyData starts automatically on macOS when the user
    logs in if the "Start Automatically" checkbox is ticked in the
    Advanced tab of the Settings dialog.
    """
    appBundlePath = "/Applications/MyData.app"
    if hasattr(sys, "frozen"):
        objectivecDir = "../MacOS"
    else:
        objectivecDir = "resources/macOS/ObjectiveC/bin"
    loginItemExistsBinary = os.path.join(objectivecDir, "loginitem-exists")
    loginItemExistsCmdList = [loginItemExistsBinary, appBundlePath]
    loginItemExists = (subprocess.call(loginItemExistsCmdList) == 0)
    if loginItemExists and SETTINGS.advanced.startAutomaticallyOnLogin:
        logger.debug("MyData is already set to start automatically on login.")
    elif not loginItemExists and SETTINGS.advanced.startAutomaticallyOnLogin:
        logger.info("Adding MyData to login items.")
        addLoginItemBinary = os.path.join(objectivecDir, "add-loginitem")
        addLoginItemCmdList = [addLoginItemBinary, appBundlePath]
        exitCode = subprocess.call(addLoginItemCmdList)
        if exitCode != 0:
            logger.error("Received exit code %d from %s"
                         % (exitCode, addLoginItemCmdList))
    elif loginItemExists and not SETTINGS.advanced.startAutomaticallyOnLogin:
        logger.info("Removing MyData from login items.")
        deleteLoginItemBinary = os.path.join(objectivecDir, "delete-loginitem")
        deleteLoginItemCmdList = [deleteLoginItemBinary, appBundlePath]
        exitCode = subprocess.call(deleteLoginItemCmdList)
        if exitCode != 0:
            logger.error("Received exit code %d from %s"
                         % (exitCode, deleteLoginItemCmdList))


def UpdateLinuxAutostartFile():
    """
    Ensure that MyData starts automatically on Linux when the user
    logs in if the "Start Automatically" checkbox is ticked in the
    Advanced tab of the Settings dialog.
    """
    autostartDir = os.path.join(os.path.expanduser('~'),
                                ".config", "autostart")
    if SETTINGS.advanced.startAutomaticallyOnLogin:
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

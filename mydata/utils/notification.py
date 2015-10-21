"""
For balloon notifications near MyData's system tray icon (Windows)
or menu bar icon (Mac OS X).
"""
import subprocess
import sys
import os
import wx

from mydata.logs import logger


# pylint: disable=too-few-public-methods
class Notification(object):
    """
    For balloon notifications near MyData's system tray icon (Windows)
    or menu bar icon (Mac OS X).
    """
    @staticmethod
    def Notify(message, subtitle=None, title="MyData"):
        """
        Post notification.
        """
        if sys.platform.startswith("win"):
            wx.GetApp().taskBarIcon.ShowBalloon(title, message)
            return
        path = "resources/macosx/MyData Notifications.app/Contents/MacOS"
        executable = "MyData Notifications"
        args = ["-message", message, "-title", title, "-sound", "Purr"]
        if subtitle:
            args = args + ["-subtitle", subtitle]
        if hasattr(sys, "frozen"):
            args = args + ["-activate", "org.mytardis.MyData"]
        else:
            args = args + ["-activate", "org.python.python"]
        if hasattr(sys, "frozen"):
            path = "../MacOS"
        else:
            path = "resources/macosx/MyData Notifications.app/Contents/MacOS"
        proc = subprocess.Popen([os.path.join(path, executable)] + args,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        stdout, _ = proc.communicate()
        if proc.returncode != 0:
            logger.error(stdout)

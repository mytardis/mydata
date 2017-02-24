"""
For balloon notifications near MyData's system tray icon (Windows)
or menu bar icon (Mac OS X).
"""
import subprocess
import sys
import os
import wx

from ..logs import logger
from ..media import MYDATA_ICONS


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
        if sys.platform.startswith("linux"):
            try:
                icon = MYDATA_ICONS.GetIconPath("favicon", vendor="MyTardis")
                args = ["-i", icon, "-t", "3000", title, message]
                proc = subprocess.Popen(["notify-send"] + args,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
                stdout, _ = proc.communicate()
                if proc.returncode != 0:
                    logger.error(stdout)
            except:
                sys.stderr.write(message + "\n")
            return
        executable = "MyData Notifications"
        args = ["-message", message, "-title", title]
        if subtitle:
            args += ["-subtitle", subtitle]
        if hasattr(sys, "frozen"):
            args += ["-activate", "org.mytardis.MyData"]
        else:
            args += ["-activate", "org.python.python"]
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

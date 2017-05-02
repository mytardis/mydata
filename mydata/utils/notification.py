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
            # Need a try/except here, because we've occasionally seen errors
            # like this:
            # wx._core.PyAssertionError: C++ assertion "m_iconAdded" failed at
            # ..\..\src\msw\taskbar.cpp(255) in wxTaskBarIcon::ShowBalloon():
            # can't be used before the icon is created
            try:
                wx.GetApp().frame.taskBarIcon.ShowBalloon(title, message)
            except:
                sys.stderr.write("%s\n" % message)
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
        executable = \
            "MyData Notifications.app/Contents/MacOS/MyData Notifications"
        args = ["-message", message, "-title", title]
        if subtitle:
            args += ["-subtitle", subtitle]
        if hasattr(sys, "frozen"):
            args += ["-activate", "org.mytardis.MyData"]
        else:
            args += ["-activate", "org.python.python"]
        if hasattr(sys, "frozen"):
            path = os.path.dirname(sys.executable)
        else:
            path = "resources/macOS"
        proc = subprocess.Popen([os.path.join(path, executable)] + args,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        stdout, _ = proc.communicate()
        if proc.returncode != 0:
            logger.error(stdout)

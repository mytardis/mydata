import subprocess
import sys
import os
import wx


class Notification(object):
    @staticmethod
    def notify(message, subtitle=None, title="MyData"):
        if sys.platform.startswith("win"):
            wx.GetApp().taskBarIcon.ShowBalloon(title, message)
            return
        path = "resources/macosx/mydata-notifier.app/Contents/MacOS"
        executable = "mydata-notifier"
        args = ["-message", message, "-title", title]
        if subtitle:
            args = args + ["-subtitle", subtitle]
        if hasattr(sys, "frozen"):
            path = "../MacOS"
        else:
            path = "resources/macosx/mydata-notifier.app/Contents/MacOS"
        proc = subprocess.Popen([os.path.join(path, executable)] + args,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        stdout, _ = proc.communicate()

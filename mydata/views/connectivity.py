"""
mydata/views/connectivity.py
"""
import sys
import threading

import wx

from mydata.utils.exceptions import NoActiveNetworkInterface


def ReportNoActiveInterfaces():
    """
    Report a lack of connectivity (no active network interfaces).
    """
    message = "No active network interfaces." \
        "\n\n" \
        "Please ensure that you have an active " \
        "network interface (e.g. Ethernet or WiFi)."

    def ShowDialog():
        """
        Show error dialog in main thread.
        """
        dlg = wx.MessageDialog(None, message, "MyData",
                               wx.OK | wx.ICON_ERROR)
        if wx.PyApp.IsMainLoopRunning():
            dlg.ShowModal()
        else:
            sys.stderr.write("%s\n" % message)
        wx.GetApp().GetMainFrame().SetStatusMessage("")

    if wx.PyApp.IsMainLoopRunning():
        if threading.current_thread().name == "MainThread":
            ShowDialog()
        else:
            wx.CallAfter(ShowDialog)
    else:
        raise NoActiveNetworkInterface(message)

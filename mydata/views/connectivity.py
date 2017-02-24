"""
mydata/views/connectivity.py
"""
import wx

from ..utils.exceptions import NoActiveNetworkInterface


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
        dlg = wx.MessageDialog(None, message, "MyData", wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        wx.GetApp().GetMainFrame().SetStatusMessage("")

    if wx.PyApp.IsMainLoopRunning():
        wx.CallAfter(ShowDialog)
    else:
        raise NoActiveNetworkInterface(message)

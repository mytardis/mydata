"""
Functionality related to checking network connectivity
"""
from datetime import datetime

import netifaces
import wx

from ..constants import CONNECTIVITY_CHECK_INTERVAL as CHECK_INTERVAL
from ..logs import logger
from ..views.connectivity import ReportNoActiveInterfaces
from . import HandleGenericErrorWithDialog
from . import BeginBusyCursorIfRequired
from . import EndBusyCursorIfRequired


class Connectivity(object):
    """
    Methods for checking network connectivity
    """
    def __init__(self):
        self.activeNetworkInterface = None
        self.lastCheckSuccess = False
        self.lastCheckTime = datetime.fromtimestamp(0)

    def CheckForRefresh(self, nextEvent=None):
        """
        This method determines if a network connectivity check is due,
        and if so, posts a check connectivity event, and returns True
        to indicate that the event has been posted.

        Called from OnRefresh (the main method for scanning data folders
        and uploading data).
        """
        from ..events import MYDATA_EVENTS
        from ..events import PostEvent
        intervalSinceLastCheck = datetime.now() - self.lastCheckTime
        if intervalSinceLastCheck.total_seconds() >= CHECK_INTERVAL or \
                not self.lastCheckSuccess:
            logger.debug("Checking network connectivity...")
            checkConnectivityEvent = \
                MYDATA_EVENTS.CheckConnectivityEvent(nextEvent=nextEvent)
            PostEvent(checkConnectivityEvent)
            return True
        return False

    def Check(self, event):
        """
        Check network connectivity
        """
        from ..events import PostEvent
        wx.CallAfter(BeginBusyCursorIfRequired)
        try:
            activeNetworkInterfaces = Connectivity.GetActiveNetworkInterfaces()
        except Exception as err:
            HandleGenericErrorWithDialog(err)
        wx.CallAfter(EndBusyCursorIfRequired, event)
        if len(activeNetworkInterfaces) > 0:
            logger.debug("Found at least one active network interface: %s."
                         % activeNetworkInterfaces[0])
            self.lastCheckSuccess = True
            self.lastCheckTime = datetime.now()
            self.activeNetworkInterface = activeNetworkInterfaces[0]
            if hasattr(event, "nextEvent") and event.nextEvent:
                PostEvent(event.nextEvent)
        else:
            self.lastCheckSuccess = False
            self.lastCheckTime = datetime.now()
            self.activeNetworkInterface = None
            ReportNoActiveInterfaces()

    def NeedToCheck(self):
        """
        Return True if a connectivity check is needed
        """
        intervalSinceLastCheck = datetime.now() - self.lastCheckTime
        return intervalSinceLastCheck.total_seconds() >= CHECK_INTERVAL \
            or not self.lastCheckSuccess

    @staticmethod
    def GetDefaultInterfaceType():
        """
        Get default interface type
        """
        defaultInterfaceType = netifaces.AF_INET
        if defaultInterfaceType not in netifaces.gateways()['default'].keys():
            defaultInterfaceType = netifaces.AF_INET6
        if defaultInterfaceType not in netifaces.gateways()['default'].keys():
            defaultInterfaceType = netifaces.AF_LINK
        if defaultInterfaceType not in netifaces.gateways()['default'].keys():
            defaultInterfaceType = None
        return defaultInterfaceType

    @staticmethod
    def GetActiveNetworkInterfaces():
        """
        Get active network interfaces
        """
        logger.debug("Determining the active network interface...")
        activeInterfaces = []
        defaultInterfaceType = Connectivity.GetDefaultInterfaceType()
        if defaultInterfaceType:
            activeInterfaces.append(
                netifaces.gateways()['default'][defaultInterfaceType][1])
        return activeInterfaces

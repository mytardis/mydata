"""
Tests to be run with nosetests
"""
import os
import sys
import tempfile
import unittest

import wx

from ..events import MYDATA_EVENTS
from .utils import StartFakeMyTardisServer
from .utils import WaitForFakeMyTardisServerToStart
if sys.platform.startswith("linux"):
    from ..linuxsubprocesses import StopErrandBoy


class MyDataTester(unittest.TestCase):
    """
    Base class for inheriting from for tests requiring a fake MyTardis server
    """
    def __init__(self, *args, **kwargs):
        super(MyDataTester, self).__init__(*args, **kwargs)
        self.app = None
        self.frame = None
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.fakeMyTardisUrl = None

    def setUp(self):
        MYDATA_EVENTS.InitializeWithNotifyWindow(self.frame)
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        WaitForFakeMyTardisServerToStart(self.fakeMyTardisUrl)

    def InitializeAppAndFrame(self, title):
        """
        Initialize generic wxPython app and main frame
        """
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, title=title)

    def tearDown(self):
        if self.frame:
            self.frame.Hide()
            self.frame.Destroy()
        if self.httpd:
            self.httpd.shutdown()
        if self.fakeMyTardisServerThread:
            self.fakeMyTardisServerThread.join()
        if sys.platform.startswith("linux"):
            StopErrandBoy()


class MyDataSettingsTester(MyDataTester):
    """
    Base class for inheriting from for tests requiring a fake MyTardis server
    """
    def __init__(self, *args, **kwargs):
        super(MyDataSettingsTester, self).__init__(*args, **kwargs)
        # Used for saving MyData.cfg:
        self.tempFilePath = None

    def setUp(self):
        super(MyDataSettingsTester, self).setUp()
        with tempfile.NamedTemporaryFile() as tempConfig:
            self.tempFilePath = tempConfig.name

    def tearDown(self):
        super(MyDataSettingsTester, self).tearDown()
        if os.path.exists(self.tempFilePath):
            os.remove(self.tempFilePath)

class MyDataScanFoldersTester(MyDataTester):
    """
    Base class for inheriting from for tests requiring a fake MyTardis server

    Includes callbacks used by ScanFolders.
    """
    @staticmethod
    def IncrementProgressDialog():
        """
        Callback for ScanFolders.
        """
        pass

    @staticmethod
    def ShouldAbort():
        """
        Callback for ScanFolders.
        """
        return False

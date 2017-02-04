"""
Test ability to use MyData's Test Run.
"""
import os
import sys
import time
import tempfile
import threading
import unittest
from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn

import wx
import requests

from mydata.MyData import MyData
from mydata.events import MYDATA_EVENTS
from mydata.models.settings import SettingsModel
from mydata.tests.fake_mytardis_server import FakeMyTardisHandler
from mydata.tests.utils import GetEphemeralPort
if sys.platform.startswith("linux"):
    from mydata.linuxsubprocesses import StopErrandBoy

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class MyDataAppInstanceTester(unittest.TestCase):
    """
    Test ability to use MyData's Test Run.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(MyDataAppInstanceTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.mydataApp = None

    def setUp(self):
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = SettingsModel(configPath=configPath, checkForUpdates=False)
        self.tempConfig = tempfile.NamedTemporaryFile()
        self.tempFilePath = self.tempConfig.name
        self.tempConfig.close()
        self.settingsModel.SetConfigPath(self.tempFilePath)
        self.StartFakeMyTardisServer()
        self.settingsModel.SetMyTardisUrl(
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort))
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        self.settingsModel.SetDataDirectory(dataDirectory)
        self.settingsModel.SaveToDisk()

    def test_mydata_test_run(self):
        """
        Test ability to use MyData's Test Run.
        """
        sys.stderr.write("Waiting for fake MyTardis server to start...\n")
        attempts = 0
        while True:
            try:
                attempts += 1
                requests.get(self.settingsModel.GetMyTardisUrl() + "/api/v1/?format=json",
                             timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (self.settingsModel.GetMyTardisUrl(),
                                       str(err)))

        settingsValidation = self.settingsModel.Validate()
        self.assertTrue(settingsValidation.IsValid())
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'],
                                settingsModel=self.settingsModel)

        popupMenu = self.mydataApp.taskBarIcon.CreatePopupMenu()

        # Just for test coverage:
        self.mydataApp.LogOnRefreshCaller(event=None, jobId=1)
        self.mydataApp.LogOnRefreshCaller(event=None, jobId=None)
        pyEvent = wx.PyEvent()
        jobId = None
        pyEvent.SetId(self.mydataApp.settingsTool.GetId())
        self.mydataApp.LogOnRefreshCaller(pyEvent, jobId)
        pyEvent.SetId(self.mydataApp.uploadTool.GetId())
        self.mydataApp.LogOnRefreshCaller(pyEvent, jobId)
        # Requires popupMenu (defined above):
        pyEvent.SetId(self.mydataApp.taskBarIcon.GetSyncNowMenuItem().GetId())
        self.mydataApp.LogOnRefreshCaller(pyEvent, jobId)
        mydataEvent = MYDATA_EVENTS.ValidateSettingsForRefreshEvent()
        self.mydataApp.LogOnRefreshCaller(mydataEvent, jobId)
        mydataEvent = MYDATA_EVENTS.SettingsValidationCompleteEvent()
        self.mydataApp.LogOnRefreshCaller(mydataEvent, jobId)
        mydataEvent = MYDATA_EVENTS.ShutdownForRefreshCompleteEvent()
        self.mydataApp.LogOnRefreshCaller(mydataEvent, jobId)
        mydataEvent = MYDATA_EVENTS.SettingsValidationCompleteEvent()
        self.mydataApp.LogOnRefreshCaller(mydataEvent, jobId)
        pyEvent = wx.PyEvent()
        pyEvent.SetEventType(12345)
        self.mydataApp.LogOnRefreshCaller(pyEvent, jobId)

        popupMenu.Destroy()

        # Test opening webpages using fake MyTardis URL.
        pyEvent = wx.PyEvent()
        self.mydataApp.OnMyTardis(pyEvent)
        self.mydataApp.OnAbout(pyEvent)

        # When running MyData without an event loop, this will block until complete:
        self.mydataApp.OnTestRunFromToolbar(event=wx.PyEvent())

    def tearDown(self):
        self.mydataApp.GetTestRunFrame().Hide()
        self.mydataApp.GetMainFrame().Hide()
        self.mydataApp.GetMainFrame().Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()
        if os.path.exists(self.tempFilePath):
            os.remove(self.tempFilePath)
        if sys.platform.startswith("linux"):
            StopErrandBoy()

    def StartFakeMyTardisServer(self):
        """
        Start fake MyTardis server.
        """
        self.fakeMyTardisPort = GetEphemeralPort()
        self.httpd = ThreadedHTTPServer((self.fakeMyTardisHost, self.fakeMyTardisPort),
                                        FakeMyTardisHandler)

        def FakeMyTardisServer():
            """ Run fake MyTardis server """
            self.httpd.serve_forever()
        self.fakeMyTardisServerThread = \
            threading.Thread(target=FakeMyTardisServer,
                             name="FakeMyTardisServerThread")
        self.fakeMyTardisServerThread.start()

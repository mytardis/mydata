"""
Test ability to open submit debug report dialog.
"""
import unittest
import os
import sys
import time
import threading
from BaseHTTPServer import HTTPServer

import requests
import wx

from mydata.models.settings import SettingsModel
from mydata.tests.fake_submit_debug_log_server import FakeSubmitDebugLogHandler
from mydata.tests.utils import GetEphemeralPort
from mydata.logs import logger


class SubmitDebugLogTester(unittest.TestCase):
    """
    Test ability to open submit debug report dialog.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(SubmitDebugLogTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.app = None
        self.frame = None
        self.settingsModel = None
        self.submitDebugReportDialog = None
        self.fakeSubmitDebugLogServerHost = "127.0.0.1"
        self.fakeSubmitDebugLogServerPort = None
        self.fakeSubmitDebugLogServerThread = None

    def setUp(self):
        """
        If we're creating a wx application in the test, it's
        safest to do it in setUp, because we know that setUp
        will only be called once, so only one app will be created.
        """
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title="Submit Debug Log Dialog test")
        self.frame.Show()
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = SettingsModel(configPath=configPath, checkForUpdates=False)
        self.StartFakeSubmitDebugLogServer()

    def tearDown(self):
        """
        Destroy app's main frame, terminating app.
        """
        self.frame.Hide()
        self.frame.Destroy()
        self.httpd.shutdown()
        self.fakeSubmitDebugLogServerThread.join()

    def test_submit_debug_report_dialog(self):
        """
        Test ability to open submit debug report dialog.
        """
        sys.stderr.write("Waiting for fake Submit Debug Log server to start...\n")
        attempts = 0
        url = "http://%s:%s" % (self.fakeSubmitDebugLogServerHost,
                                self.fakeSubmitDebugLogServerPort)
        while True:
            try:
                attempts += 1
                requests.head(url, timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (url, str(err)))
        logContent = ""
        for i in range(5050):
            logContent += "ERROR %s\n" % i
        logger.error(logContent)
        _ = logger.GenerateDebugLogContent(self.settingsModel)
        logger.SubmitLog(self.frame, self.settingsModel,
                         url="http://%s:%s"
                         % (self.fakeSubmitDebugLogServerHost,
                            self.fakeSubmitDebugLogServerPort))

    def StartFakeSubmitDebugLogServer(self):
        """
        Start fake Submit Debug Log server.
        """
        self.fakeSubmitDebugLogServerPort = GetEphemeralPort()
        self.httpd = HTTPServer((self.fakeSubmitDebugLogServerHost,
                                 self.fakeSubmitDebugLogServerPort),
                                FakeSubmitDebugLogHandler)

        def FakeSubmitDebugLogServer():
            """ Run fake Submit Debug Log server """
            self.httpd.serve_forever()
        self.fakeSubmitDebugLogServerThread = \
            threading.Thread(target=FakeSubmitDebugLogServer,
                             name="FakeSubmitDebugLogServerThread")
        self.fakeSubmitDebugLogServerThread.start()

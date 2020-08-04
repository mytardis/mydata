"""
Test ability to open submit debug report dialog.
"""
import sys
import time
import threading

from http.server import HTTPServer

import requests
import wx

from ...settings import SETTINGS
from ...logs import logger
from ..fake_submit_debug_log_server import FakeSubmitDebugLogHandler
from ..utils import GetEphemeralPort
from .. import MyApp, MyDataGuiTester


class SubmitDebugLogTester(MyDataGuiTester):
    """
    Test ability to open submit debug report dialog.
    """
    def __init__(self, *args, **kwargs):
        super(SubmitDebugLogTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.app = None
        self.frame = None
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
        self.app = MyApp()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title="Submit Debug Log Dialog test")
        self.frame.Show()
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        self.StartFakeSubmitDebugLogServer()

    def tearDown(self):
        """
        Close app's main frame, terminating app.
        """
        self.frame.Hide()
        self.httpd.shutdown()
        self.fakeSubmitDebugLogServerThread.join()

    def test_submit_debug_report_dialog(self):
        """Test ability to open submit debug report dialog.
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
            except requests.exceptions.ConnectionError as err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (url, str(err)))
        logContent = ""
        for i in range(5050):
            logContent += "ERROR %s\n" % i
        logger.error(logContent)
        _ = logger.GenerateDebugLogContent(SETTINGS)
        logger.SubmitLog(self.frame, SETTINGS,
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

"""
Test ability to read and validate scheduling config.
"""
from datetime import datetime
import os
import sys
import time
import unittest
import threading
from BaseHTTPServer import HTTPServer

import requests
import wx

from mydata.models.settings import SettingsModel
from mydata.tests.fake_mytardis_server import FakeMyTardisHandler
from mydata.tests.utils import GetEphemeralPort


class SchedulingConfigTester(unittest.TestCase):
    """
    Test ability to read and validate scheduling config.
    """
    def __init__(self, *args, **kwargs):
        super(SchedulingConfigTester, self).__init__(*args, **kwargs)
        self.app = None
        self.frame = None
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.fakeMyTardisUrl = None

    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title='SchedulingConfigTester')
        self.StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        self.WaitForFakeMyTardisServerToStart()

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()

    def test_read_timer_cfg(self):
        """
        Test ability to read Timer settings from MyData.cfg
        """
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataTimer.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.SetDataDirectory(dataDirectory)
        settingsModel.SetMyTardisUrl(self.fakeMyTardisUrl)
        self.assertEqual(settingsModel.GetScheduleType(), "Timer")
        self.assertEqual(settingsModel.GetTimerMinutes(), 15)
        timerFromTime = \
            datetime.time(datetime.strptime("00:00:00", "%H:%M:%S"))
        self.assertEqual(settingsModel.GetTimerFromTime(), timerFromTime)
        timerToTime = \
            datetime.time(datetime.strptime("23:59:00", "%H:%M:%S"))
        self.assertEqual(settingsModel.GetTimerToTime(), timerToTime)
        settingsValidation = settingsModel.Validate()
        self.assertTrue(settingsValidation.IsValid())

    def test_read_weekly_cfg(self):
        """
        Test ability to read Weekly schedule settings from MyData.cfg
        """
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataWeekly.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.SetDataDirectory(dataDirectory)
        settingsModel.SetMyTardisUrl(self.fakeMyTardisUrl)
        self.assertEqual(settingsModel.GetScheduleType(), "Weekly")
        self.assertEqual(settingsModel.IsMondayChecked(), True)
        self.assertEqual(settingsModel.IsTuesdayChecked(), False)
        settingsValidation = settingsModel.Validate()
        self.assertTrue(settingsValidation.IsValid())

    def StartFakeMyTardisServer(self):
        """
        Start fake MyTardis server.
        """
        self.fakeMyTardisPort = GetEphemeralPort()
        self.httpd = HTTPServer((self.fakeMyTardisHost, self.fakeMyTardisPort),
                                FakeMyTardisHandler)

        def FakeMyTardisServer():
            """ Run fake MyTardis server """
            self.httpd.serve_forever()
        self.fakeMyTardisServerThread = \
            threading.Thread(target=FakeMyTardisServer,
                             name="FakeMyTardisServerThread")
        self.fakeMyTardisServerThread.start()

    def WaitForFakeMyTardisServerToStart(self):
        """
        Wait for fake MyTardis server to start.
        """
        sys.stderr.write("Waiting for fake MyTardis server to start...\n")
        attempts = 0
        while True:
            try:
                attempts += 1
                requests.get(self.fakeMyTardisUrl +
                             "/api/v1/?format=json", timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (self.fakeMyTardisUrl, str(err)))


if __name__ == '__main__':
    unittest.main()

"""
Test Weekly schedule type.
"""
from datetime import datetime
from datetime import timedelta
import os
import sys
import time
import tempfile
import threading
import unittest
from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn

import requests

from mydata.MyData import MyData
from mydata.models.settings import SettingsModel
from mydata.tests.fake_mytardis_server import FakeMyTardisHandler
from mydata.tests.utils import GetEphemeralPort
if sys.platform.startswith("linux"):
    from mydata.linuxsubprocesses import StopErrandBoy

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class WeeklyScheduleTester(unittest.TestCase):
    """
    Test Weekly schedule type.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(WeeklyScheduleTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisUrl = None
        self.fakeMyTardisServerThread = None
        self.mydataApp = None

    def setUp(self):
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/testdataUsernameDataset_POST.cfg")
        self.settingsModel = SettingsModel(configPath=configPath, checkForUpdates=False)
        self.tempConfig = tempfile.NamedTemporaryFile()
        self.tempFilePath = self.tempConfig.name
        self.tempConfig.close()
        self.settingsModel.SetConfigPath(self.tempFilePath)
        self.StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        self.settingsModel.SetMyTardisUrl(self.fakeMyTardisUrl)
        self.settingsModel.SetDataDirectory(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "testdata", "testdataUsernameDataset"))
        self.settingsModel.SetScheduleType("Weekly")
        self.settingsModel.SetMondayChecked(True)
        self.settingsModel.SetTuesdayChecked(True)
        self.settingsModel.SetWednesdayChecked(True)
        self.settingsModel.SetThursdayChecked(False)
        self.settingsModel.SetFridayChecked(True)
        self.settingsModel.SetSaturdayChecked(True)
        self.settingsModel.SetSundayChecked(True)
        self.settingsModel.SetScheduledTime(
            datetime.time(datetime.now().replace(microsecond=0) +
                          timedelta(minutes=1)))
        self.settingsModel.SaveToDisk()

    def test_weekly_schedule(self):
        """
        Test Weekly schedule type.
        """
        self.WaitForFakeMyTardisServerToStart()
        settingsValidation = self.settingsModel.Validate()
        self.assertTrue(settingsValidation.IsValid())
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'],
                                settingsModel=self.settingsModel)
        self.mydataApp.taskBarIcon.CreatePopupMenu()
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 6)
        # TO DO: A way of testing that additional tasks are scheduled,
        # according to the timer interval.
        self.assertEqual(self.mydataApp.tasksModel.GetRowCount(), 1)
        self.assertEqual(self.mydataApp.tasksModel.GetValueByRow(0, 4), "Weekly (MTW-FSS)")
        self.mydataApp.tasksModel.DeleteAllRows()
        self.assertEqual(self.mydataApp.tasksModel.GetRowCount(), 0)

    def tearDown(self):
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

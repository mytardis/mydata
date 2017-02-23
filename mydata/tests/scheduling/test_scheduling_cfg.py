"""
Test ability to read and validate scheduling config.
"""
from datetime import datetime
import os
import unittest

import wx

from mydata.models.settings import SettingsModel
from mydata.models.settings.validation import ValidateSettings
from mydata.tests.utils import StartFakeMyTardisServer
from mydata.tests.utils import WaitForFakeMyTardisServerToStart


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
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        WaitForFakeMyTardisServerToStart(self.fakeMyTardisUrl)

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
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        self.assertEqual(settingsModel.schedule.scheduleType, "Timer")
        self.assertEqual(settingsModel.schedule.timerMinutes, 15)
        timerFromTime = \
            datetime.time(datetime.strptime("00:00:00", "%H:%M:%S"))
        self.assertEqual(settingsModel.schedule.timerFromTime, timerFromTime)
        timerToTime = \
            datetime.time(datetime.strptime("23:59:00", "%H:%M:%S"))
        self.assertEqual(settingsModel.schedule.timerToTime, timerToTime)
        ValidateSettings(settingsModel)

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
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        self.assertEqual(settingsModel.schedule.scheduleType, "Weekly")
        self.assertEqual(settingsModel.schedule.mondayChecked, True)
        self.assertEqual(settingsModel.schedule.tuesdayChecked, False)
        ValidateSettings(settingsModel)

"""
Test Timer schedule type.
"""
from datetime import datetime
import os
import sys
import tempfile
import unittest

from ...MyData import MyData
from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from ..utils import StartFakeMyTardisServer
from ..utils import WaitForFakeMyTardisServerToStart
if sys.platform.startswith("linux"):
    from ...linuxsubprocesses import StopErrandBoy


class TimerScheduleTester(unittest.TestCase):
    """
    Test Timer schedule type.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(TimerScheduleTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisUrl = None
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
        self.settingsModel.configPath = self.tempFilePath
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        self.settingsModel.general.dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.settingsModel.schedule.scheduleType = "Timer"
        self.settingsModel.schedule.timerMinutes = 15
        self.settingsModel.schedule.timerFromTime = \
            datetime.time(datetime.strptime("12:00 AM", "%I:%M %p"))
        self.settingsModel.schedule.timerToTime = \
            datetime.time(datetime.strptime("11:59 PM", "%I:%M %p"))
        SaveSettingsToDisk(self.settingsModel)

    def test_timer_schedule(self):
        """
        Test Timer schedule type.
        """
        WaitForFakeMyTardisServerToStart(self.fakeMyTardisUrl)
        ValidateSettings(self.settingsModel)
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'],
                                settingsModel=self.settingsModel)
        self.mydataApp.taskBarIcon.CreatePopupMenu()
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 7)
        # TO DO: A way of testing that additional tasks are scheduled,
        # according to the timer interval.

    def tearDown(self):
        self.mydataApp.GetMainFrame().Hide()
        self.mydataApp.GetMainFrame().Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()
        if os.path.exists(self.tempFilePath):
            os.remove(self.tempFilePath)
        if sys.platform.startswith("linux"):
            StopErrandBoy()

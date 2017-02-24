"""
Test Weekly schedule type.
"""
from datetime import datetime
from datetime import timedelta
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
        self.settingsModel.schedule.scheduleType = "Weekly"
        self.settingsModel.schedule.mondayChecked = True
        self.settingsModel.schedule.tuesdayChecked = True
        self.settingsModel.schedule.wednesdayChecked = True
        self.settingsModel.schedule.thursdayChecked = False
        self.settingsModel.schedule.fridayChecked = True
        self.settingsModel.schedule.saturdayChecked = True
        self.settingsModel.schedule.sundayChecked = True
        self.settingsModel.schedule.scheduledTime = \
            datetime.time(datetime.now().replace(microsecond=0) +
                          timedelta(minutes=1))
        SaveSettingsToDisk(self.settingsModel)

    def test_weekly_schedule(self):
        """
        Test Weekly schedule type.
        """
        WaitForFakeMyTardisServerToStart(self.fakeMyTardisUrl)
        ValidateSettings(self.settingsModel)
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'],
                                settingsModel=self.settingsModel)
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 7)
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

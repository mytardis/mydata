"""
Test Once schedule type with invalid date/time.
"""
from datetime import datetime
from datetime import timedelta
import os
import sys
import tempfile
import unittest

from mydata.MyData import MyData
from mydata.models.settings import SettingsModel
from mydata.models.settings.serialize import SaveSettingsToDisk
from mydata.models.settings.validation import ValidateSettings
from mydata.utils.exceptions import InvalidSettings
from mydata.tests.utils import StartFakeMyTardisServer
from mydata.tests.utils import WaitForFakeMyTardisServerToStart
if sys.platform.startswith("linux"):
    from mydata.linuxsubprocesses import StopErrandBoy


class OnceScheduleTester(unittest.TestCase):
    """
    Test Once schedule type with invalid date/time.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(OnceScheduleTester, self).__init__(*args, **kwargs)
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
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        self.settingsModel.general.dataDirectory = dataDirectory
        self.settingsModel.schedule.scheduleType = "Once"
        self.settingsModel.schedule.scheduledDate = \
            datetime.date(datetime.now())
        self.settingsModel.schedule.scheduledTime = \
            datetime.time(datetime.now().replace(microsecond=0) -
                          timedelta(minutes=1))
        SaveSettingsToDisk(self.settingsModel)

    def test_once_schedule(self):
        """
        Test Once schedule type with invalid date/time.
        """
        WaitForFakeMyTardisServerToStart(self.fakeMyTardisUrl)
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "scheduled_time")
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'],
                                settingsModel=self.settingsModel)
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 0)
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

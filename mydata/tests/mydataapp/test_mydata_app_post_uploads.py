"""
Test ability to create a MyData App instance and uploads files using POST.
"""
import os

from .. import MyDataSettingsTester
from ...MyData import MyData
from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings


class MyDataAppInstanceTester(MyDataSettingsTester):
    """
    Test ability to create MyData App instance and upload files using POST.
    """
    def __init__(self, *args, **kwargs):
        super(MyDataAppInstanceTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(MyDataAppInstanceTester, self).setUp()
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = \
            SettingsModel(configPath=configPath, checkForUpdates=False)
        self.settingsModel.configPath = self.tempFilePath
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        self.settingsModel.general.dataDirectory = dataDirectory
        SaveSettingsToDisk(self.settingsModel)

    def test_mydata_app_post_uploads(self):
        """
        Test ability to create MyData App instance and upload files using POST.
        """
        ValidateSettings(self.settingsModel)
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'],
                                settingsModel=self.settingsModel)
        self.mydataApp.taskBarIcon.CreatePopupMenu()
        # When running MyData without an event loop, this will block until complete:
        self.mydataApp.OnRefresh(event=None, needToValidateSettings=False)
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        self.assertEqual(self.mydataApp.uploadsModel.GetCompletedCount(), 7)
        uploadsModel = self.mydataApp.uploadsModel
        statusColumn = 5
        self.assertEqual(uploadsModel.GetValueByRow(0, statusColumn),
                         uploadsModel.completedIcon)
        progressColumn = 6
        self.assertEqual(uploadsModel.GetValueByRow(0, progressColumn), 100)
        messageColumn = 7
        self.assertEqual(uploadsModel.GetValueByRow(0, messageColumn),
                         "Upload complete!")

    def tearDown(self):
        super(MyDataAppInstanceTester, self).tearDown()
        if self.mydataApp:
            self.mydataApp.GetMainFrame().Hide()
            self.mydataApp.GetMainFrame().Destroy()

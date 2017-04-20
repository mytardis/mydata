"""
Test ability to create a MyData App instance and uploads files using POST.
"""
from ...MyData import MyData
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.validation import ValidateSettings
from .. import MyDataSettingsTester


class MyDataAppInstanceTester(MyDataSettingsTester):
    """
    Test ability to create MyData App instance and upload files using POST.
    """
    def __init__(self, *args, **kwargs):
        super(MyDataAppInstanceTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(MyDataAppInstanceTester, self).setUp()
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        SaveSettingsToDisk()

    def test_mydata_app_post_uploads(self):
        """
        Test ability to create MyData App instance and upload files using POST.
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        self.mydataApp.frame.taskBarIcon.CreatePopupMenu()
        # When running MyData without an event loop, this will block until complete:
        self.mydataApp.OnRefresh(event=None, needToValidateSettings=False)
        # testdataUsernameDataset_POST.cfg has upload_invalid_user_folders = True,
        # so INVALID_USER/InvalidUserDataset1/InvalidUserFile1.txt is included
        # in the uploads completed count:
        uploadsModel = self.mydataApp.dataViewModels['uploads']
        self.assertEqual(uploadsModel.GetCompletedCount(), 7)
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
            self.mydataApp.frame.Hide()
            self.mydataApp.frame.Destroy()

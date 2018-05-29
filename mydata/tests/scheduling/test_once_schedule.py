"""
Test Once schedule type.
"""
from datetime import datetime
from datetime import timedelta

from ...settings import SETTINGS
from ...MyData import MyData
from ...dataviewmodels.dataview import DATAVIEW_MODELS
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import InvalidSettings
from .. import MyDataSettingsTester


class OnceScheduleTester(MyDataSettingsTester):
    """
    Test Once schedule type
    """
    def __init__(self, *args, **kwargs):
        super(OnceScheduleTester, self).__init__(*args, **kwargs)
        self.mydataApp = None

    def setUp(self):
        super(OnceScheduleTester, self).setUp()
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")
        SETTINGS.schedule.scheduleType = "Once"
        SETTINGS.schedule.scheduledDate = datetime.date(datetime.now())
        SETTINGS.schedule.scheduledTime = \
            datetime.time(datetime.now().replace(microsecond=0) +
                          timedelta(minutes=1))

    def test_once_schedule(self):
        """
        Test Once schedule type
        """
        ValidateSettings()
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        self.assertEqual(DATAVIEW_MODELS['uploads'].GetCompletedCount(), 8)

    def test_once_schedule_invalid(self):
        """
        Test Once schedule type with invalid date/time
        """
        SETTINGS.schedule.scheduledTime = \
            datetime.time(datetime.now().replace(microsecond=0) -
                          timedelta(minutes=1))
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "scheduled_time")
        self.mydataApp = MyData(argv=['MyData', '--loglevel', 'DEBUG'])
        self.assertEqual(DATAVIEW_MODELS['uploads'].GetCompletedCount(), 0)

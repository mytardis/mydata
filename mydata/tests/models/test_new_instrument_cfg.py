"""
Test ability to create a new instrument when required.
"""
import os

from ...settings import SETTINGS
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from .. import MyDataTester


class NewInstrumentTester(MyDataTester):
    """
    Test ability to create a new instrument when required.
    """
    def setUp(self):
        super(NewInstrumentTester, self).setUp()
        super(NewInstrumentTester, self).InitializeAppAndFrame(
            'NewInstrumentTester')

    def test_create_new_instrument(self):
        """
        Test ability to create a new instrument when required.
        """
        pathToTestConfig = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataNewInstrument.cfg"))
        self.assertTrue(os.path.exists(pathToTestConfig))
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataDataset"))
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        ValidateSettings()
        self.assertEqual(SETTINGS.instrument.name, "New Instrument")

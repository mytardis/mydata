"""
Test ability to create a new instrument when required.
"""
import os

from .. import MyDataTester
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings


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
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataNewInstrument.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataDataset")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        ValidateSettings(settingsModel)
        self.assertEqual(settingsModel.instrument.GetName(), "New Instrument")

"""
Test ability to create a new instrument when required.
"""
from ...settings import SETTINGS
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
        self.UpdateSettingsFromCfg(
            "testdataNewInstrument",
            dataFolderName="testdataDataset")
        ValidateSettings()
        self.assertEqual(SETTINGS.general.instrument.name, "New Instrument")

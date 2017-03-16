"""
Test ability to handle instrument-related exceptions.
"""
from ...settings import SETTINGS
from ...models.instrument import InstrumentModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import InternalServerError
from .. import MyDataTester


class InstrumentExceptionsTester(MyDataTester):
    """
    Test ability to handle instrument-related exceptions.
    """
    def setUp(self):
        super(InstrumentExceptionsTester, self).setUp()
        super(InstrumentExceptionsTester, self).InitializeAppAndFrame(
            'InstrumentExceptionsTester')

    def test_instrument_exceptions(self):
        """
        Test ability to handle instrument-related exceptions.
        """
        self.UpdateSettingsFromCfg("testdataExpDataset")
        ValidateSettings()

        facility = SETTINGS.facility
        self.assertIsNotNone(facility)

        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = InstrumentModel.GetInstrument(facility,
                                              "Unauthorized Instrument")
        with self.assertRaises(Unauthorized):
            _ = InstrumentModel.CreateInstrument(facility,
                                                 "Unauthorized Instrument")
        SETTINGS.general.apiKey = apiKey

        SETTINGS.general.myTardisUrl = \
            "%s/request/http/code/500" % self.fakeMyTardisUrl
        with self.assertRaises(InternalServerError):
            _ = InstrumentModel.CreateInstrument(facility, "Instrument name")

        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        instrument = SETTINGS.instrument
        SETTINGS.general.myTardisUrl = \
            "%s/request/http/code/500" % self.fakeMyTardisUrl
        with self.assertRaises(InternalServerError):
            instrument.Rename("New instrument name")

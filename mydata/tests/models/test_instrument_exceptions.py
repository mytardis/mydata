"""
Test ability to handle instrument-related exceptions.
"""
from requests.exceptions import HTTPError

from ...settings import SETTINGS
from ...models.instrument import InstrumentModel
from ...models.settings.validation import ValidateSettings
from .. import MyDataTester


class InstrumentExceptionsTester(MyDataTester):
    """
    Test ability to handle instrument-related exceptions.
    """
    def test_instrument_exceptions(self):
        """Test ability to handle instrument-related exceptions.
        """
        self.UpdateSettingsFromCfg("testdataExpDataset")
        ValidateSettings()

        facility = SETTINGS.general.facility
        self.assertIsNotNone(facility)

        apiKey = SETTINGS.general.apiKey
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(HTTPError) as context:
            _ = InstrumentModel.GetInstrument(facility,
                                              "Unauthorized Instrument")
        self.assertEqual(context.exception.response.status_code, 401)

        with self.assertRaises(HTTPError) as context:
            _ = InstrumentModel.CreateInstrument(facility,
                                                 "Unauthorized Instrument")
        self.assertEqual(context.exception.response.status_code, 401)

        SETTINGS.general.apiKey = apiKey

        SETTINGS.general.myTardisUrl = \
            "%s/request/http/code/500" % self.fakeMyTardisUrl
        with self.assertRaises(HTTPError) as context:
            _ = InstrumentModel.CreateInstrument(facility, "Instrument name")
        self.assertEqual(context.exception.response.status_code, 500)

        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        instrument = SETTINGS.general.instrument
        SETTINGS.general.myTardisUrl = \
            "%s/request/http/code/500" % self.fakeMyTardisUrl
        with self.assertRaises(HTTPError) as context:
            instrument.Rename("New instrument name")
        self.assertEqual(context.exception.response.status_code, 500)

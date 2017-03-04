"""
Test ability to handle instrument-related exceptions.
"""
import os

from ...settings import SETTINGS
from ...models.instrument import InstrumentModel
from ...models.settings import SettingsModel
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
        # pylint: disable=too-many-locals
        pathToTestConfig = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataExpDataset.cfg"))
        self.assertTrue(os.path.exists(pathToTestConfig))
        SETTINGS.Update(SettingsModel(pathToTestConfig))
        dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataExpDataset.cfg"))
        self.assertTrue(os.path.exists(dataDirectory))
        SETTINGS.general.dataDirectory = dataDirectory
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
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

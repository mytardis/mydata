"""
Test ability to handle instrument-related exceptions.
"""
import os

from .. import MyDataTester
from ...models.instrument import InstrumentModel
from ...models.settings import SettingsModel
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import InternalServerError


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
        pathToTestConfig = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataExpDataset.cfg")
        self.assertTrue(os.path.exists(pathToTestConfig))
        settingsModel = SettingsModel(pathToTestConfig)
        dataDirectory = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataExpDataset.cfg")
        self.assertTrue(os.path.exists(dataDirectory))
        settingsModel.general.dataDirectory = dataDirectory
        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        ValidateSettings(settingsModel)

        facility = settingsModel.facility
        self.assertIsNotNone(facility)

        apiKey = settingsModel.general.apiKey
        settingsModel.general.apiKey = "invalid"
        with self.assertRaises(Unauthorized):
            _ = InstrumentModel.GetInstrument(settingsModel, facility,
                                              "Unauthorized Instrument")
        with self.assertRaises(Unauthorized):
            _ = InstrumentModel.CreateInstrument(settingsModel, facility,
                                                 "Unauthorized Instrument")
        settingsModel.general.apiKey = apiKey

        settingsModel.general.myTardisUrl = \
            "%s/request/http/code/500" % self.fakeMyTardisUrl
        with self.assertRaises(InternalServerError):
            _ = InstrumentModel.CreateInstrument(settingsModel, facility,
                                                 "Instrument name")

        settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        instrument = settingsModel.instrument
        settingsModel.general.myTardisUrl = \
            "%s/request/http/code/500" % self.fakeMyTardisUrl
        with self.assertRaises(InternalServerError):
            instrument.Rename("New instrument name")

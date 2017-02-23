"""
Test ability to handle instrument-related exceptions.
"""
import os
import unittest

import wx

from mydata.models.instrument import InstrumentModel
from mydata.models.settings import SettingsModel
from mydata.models.settings.validation import ValidateSettings
from mydata.tests.utils import StartFakeMyTardisServer
from mydata.tests.utils import WaitForFakeMyTardisServerToStart
from mydata.utils.exceptions import Unauthorized
from mydata.utils.exceptions import InternalServerError


class InstrumentExceptionsTester(unittest.TestCase):
    """
    Test ability to handle instrument-related exceptions.
    """
    def __init__(self, *args, **kwargs):
        super(InstrumentExceptionsTester, self).__init__(*args, **kwargs)
        self.app = None
        self.frame = None
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.fakeMyTardisUrl = None

    def setUp(self):
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title='InstrumentExceptionsTester')
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        WaitForFakeMyTardisServerToStart(self.fakeMyTardisUrl)

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()

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

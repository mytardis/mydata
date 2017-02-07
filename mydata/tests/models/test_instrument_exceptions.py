"""
Test ability to handle instrument-related exceptions.
"""
import os
import sys
import time
import unittest
import threading
from BaseHTTPServer import HTTPServer

import requests
import wx

from mydata.models.instrument import InstrumentModel
from mydata.models.settings import SettingsModel
from mydata.tests.fake_mytardis_server import FakeMyTardisHandler
from mydata.tests.utils import GetEphemeralPort
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
        self.StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        self.WaitForFakeMyTardisServerToStart()

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
        settingsModel.SetDataDirectory(dataDirectory)
        settingsModel.SetMyTardisUrl(self.fakeMyTardisUrl)
        settingsValidation = settingsModel.Validate()
        self.assertTrue(settingsValidation.IsValid())

        facility = settingsModel.GetFacility()
        self.assertIsNotNone(facility)

        apiKey = settingsModel.GetApiKey()
        settingsModel.SetApiKey("invalid")
        with self.assertRaises(Unauthorized):
            _ = InstrumentModel.GetInstrument(settingsModel, facility,
                                              "Unauthorized Instrument")
        with self.assertRaises(Unauthorized):
            _ = InstrumentModel.CreateInstrument(settingsModel, facility,
                                                 "Unauthorized Instrument")
        settingsModel.SetApiKey(apiKey)

        settingsModel.SetMyTardisUrl(self.fakeMyTardisUrl + "/request/http/code/500")
        with self.assertRaises(InternalServerError):
            _ = InstrumentModel.CreateInstrument(settingsModel, facility,
                                                 "Instrument name")
        instrument = settingsModel.GetInstrument()
        with self.assertRaises(InternalServerError):
            instrument.Rename("New instrument name")


    def StartFakeMyTardisServer(self):
        """
        Start fake MyTardis server.
        """
        self.fakeMyTardisPort = GetEphemeralPort()
        self.httpd = HTTPServer((self.fakeMyTardisHost, self.fakeMyTardisPort),
                                FakeMyTardisHandler)

        def FakeMyTardisServer():
            """ Run fake MyTardis server """
            self.httpd.serve_forever()
        self.fakeMyTardisServerThread = \
            threading.Thread(target=FakeMyTardisServer,
                             name="FakeMyTardisServerThread")
        self.fakeMyTardisServerThread.start()

    def WaitForFakeMyTardisServerToStart(self):
        """
        Wait for fake MyTardis server to start.
        """
        sys.stderr.write("Waiting for fake MyTardis server to start...\n")
        attempts = 0
        while True:
            try:
                attempts += 1
                requests.get(self.fakeMyTardisUrl +
                             "/api/v1/?format=json", timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (self.fakeMyTardisUrl, str(err)))

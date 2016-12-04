"""
Test ability to open settings dialog and save fields.
"""
import unittest
import tempfile
import os
import sys
import threading
import time
from BaseHTTPServer import HTTPServer

import requests
import wx

from mydata.models.settings import SettingsModel
from mydata.views.settings import SettingsDialog
from mydata.events import MYDATA_EVENTS
from mydata.events import PostEvent
from mydata.events import RenameInstrument
from mydata.utils.exceptions import DuplicateKey
from mydata.tests.fake_mytardis_server import FakeMyTardisHandler
from mydata.tests.utils import GetEphemeralPort


class SettingsDialogTester(unittest.TestCase):
    """
    Test ability to open settings dialog and save fields.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(SettingsDialogTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.app = None
        self.frame = None
        self.settingsModel = None
        self.settingsDialog = None
        self.tempConfig = None
        self.tempFilePath = None

    def setUp(self):
        """
        If we're creating a wx application in the test, it's
        safest to do it in setUp, because we know that setUp
        will only be called once, so only one app will be created.
        """
        self.app = wx.App()
        self.frame = wx.Frame(parent=None, id=wx.ID_ANY,
                              title="Settings Dialog test")
        MYDATA_EVENTS.InitializeWithNotifyWindow(self.frame)
        self.frame.Show()
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/testdataUsernameDataset_POST.cfg")
        self.settingsModel = SettingsModel(configPath=configPath, checkForUpdates=False)
        self.tempConfig = tempfile.NamedTemporaryFile()
        self.tempFilePath = self.tempConfig.name
        self.tempConfig.close()
        self.settingsModel.SetConfigPath(self.tempFilePath)
        self.StartFakeMyTardisServer()
        self.settingsModel.SetMyTardisUrl(
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort))
        self.settingsModel.SaveToDisk()
        self.settingsDialog = SettingsDialog(self.frame, self.settingsModel)

    def tearDown(self):
        if os.path.exists(self.tempFilePath):
            os.remove(self.tempFilePath)
        self.settingsDialog.Hide()
        self.frame.Hide()
        self.frame.Destroy()
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()

    def test_settings_dialog(self):
        """
        Test ability to open settings dialog and save fields.
        """
        self.settingsDialog.Show()

        # Select folder structures to test OnSelectFolderStructure:
        for folderStructure in self.settingsDialog.folderStructures:
            self.settingsDialog.SetFolderStructure(folderStructure)
            self.settingsDialog.OnSelectFolderStructure(event=None)

        # Start fake MyTardis server to test settings dialog validation:
        sys.stderr.write("Waiting for fake MyTardis server to start...\n")
        attempts = 0
        while True:
            try:
                attempts += 1
                requests.get(self.settingsModel.GetMyTardisUrl() + "/api/v1/?format=json",
                             timeout=1)
                break
            except requests.exceptions.ConnectionError, err:
                time.sleep(0.25)
                if attempts > 10:
                    raise Exception("Couldn't connect to %s: %s"
                                    % (self.settingsModel.GetMyTardisUrl(),
                                       str(err)))
        # Test settings dialog validation:
        settingsDialogValidationEvent = \
            MYDATA_EVENTS.SettingsDialogValidationEvent(
                settingsDialog=self.settingsDialog,
                settingsModel=self.settingsModel)
        PostEvent(settingsDialogValidationEvent)

        # Test updating autostart file:
        self.settingsModel.UpdateAutostartFile()

        # Test renaming instrument to an available instrument name:
        renameInstrumentEvent = MYDATA_EVENTS.RenameInstrumentEvent(
            settingsDialog=self.settingsDialog,
            settingsModel=self.settingsModel,
            facilityName=self.settingsDialog.GetFacilityName(),
            oldInstrumentName=self.settingsDialog.GetInstrumentName(),
            newInstrumentName="New Instrument")
        RenameInstrument(renameInstrumentEvent)

        # Test renaming instrument to an already used instrument name:
        renameInstrumentEvent = MYDATA_EVENTS.RenameInstrumentEvent(
            settingsDialog=self.settingsDialog,
            settingsModel=self.settingsModel,
            facilityName=self.settingsDialog.GetFacilityName(),
            oldInstrumentName=self.settingsDialog.GetInstrumentName(),
            newInstrumentName="Test Instrument2")
        with self.assertRaises(DuplicateKey):
            RenameInstrument(renameInstrumentEvent)

        # Test saving config to disk:
        self.settingsModel.SaveFieldsFromDialog(self.settingsDialog,
                                                configPath=self.tempFilePath,
                                                saveToDisk=True)
        # Test dragging and dropping a MyData.cfg onto settings dialog:
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/testdataUsernameDataset.cfg")
        self.settingsDialog.SetLocked(False)
        self.settingsDialog.OnDropFiles([configPath])

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

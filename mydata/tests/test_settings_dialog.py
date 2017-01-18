"""
Test ability to open settings dialog and save fields.
"""
from datetime import datetime
from datetime import timedelta
import os
import sys
import tempfile
import threading
import time
import unittest
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
        self.settingsModel.SetDataDirectory(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "testdata", "testdataUsernameDataset"))
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
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals

        self.settingsDialog.Show()

        # Select folder structures to test OnSelectFolderStructure:
        for folderStructure in self.settingsDialog.folderStructures:
            self.settingsDialog.SetFolderStructure(folderStructure)
            self.settingsDialog.OnSelectFolderStructure(event=None)

        # Simulate clicking Ignore Old Datasets checkbox:
        pyCommandEvent = wx.PyCommandEvent()
        self.settingsDialog.OnIgnoreOldDatasetsCheckBox(pyCommandEvent)

        # Simulate clicking Ignore Old Datasets spin control:
        self.settingsDialog.OnIgnoreOldDatasetsSpinCtrl(pyCommandEvent)

        # Simulate clicking Ignore New Files checkbox:
        self.settingsDialog.OnIgnoreNewFilesCheckBox(pyCommandEvent)

        # Simulate browsing for includes file:
        self.settingsDialog.OnBrowseIncludesFile(pyCommandEvent)

        # Simulate browsing for excludes file:
        self.settingsDialog.OnBrowseExcludesFile(pyCommandEvent)

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

        # Test settings dialog validation with invalid settings,
        # which will prompt a suggestion, based on which facilities
        # the user has access to (as a facility manager).
        # When running unittests, suggestions are automatically applied.
        self.settingsDialog.SetFacilityName("")
        settingsDialogValidationEvent = \
            MYDATA_EVENTS.SettingsDialogValidationEvent(
                settingsDialog=self.settingsDialog,
                settingsModel=self.settingsModel)
        PostEvent(settingsDialogValidationEvent)

        # Test settings dialog validation with invalid settings,
        # which will prompt a suggestion, for missing "http://"
        # in the MyTardis URL.
        # When running unittests, suggestions are automatically applied.
        myTardisUrl = self.settingsDialog.GetMyTardisUrl()
        self.settingsDialog.SetMyTardisUrl(myTardisUrl.replace("http://", ""))
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetMyTardisUrl(myTardisUrl)

        # Test settings dialog validation with invalid settings,
        # which won't prompt a suggestion, but will ensure that
        # MyData can run the relevant code which focuses the cursor
        # on the missing field:
        instrumentName = self.settingsDialog.GetInstrumentName()
        self.settingsDialog.SetInstrumentName("")
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetInstrumentName(instrumentName)

        contactName = self.settingsDialog.GetContactName()
        self.settingsDialog.SetContactName("")
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetContactName(contactName)

        contactEmail = self.settingsDialog.GetContactEmail()
        self.settingsDialog.SetContactEmail("")
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetContactEmail(contactEmail)

        dataDirectory = self.settingsDialog.GetDataDirectory()
        self.settingsDialog.SetDataDirectory("")
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetDataDirectory(dataDirectory)

        username = self.settingsDialog.GetUsername()
        self.settingsDialog.SetUsername("")
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetUsername(username)

        apiKey = self.settingsDialog.GetApiKey()
        self.settingsDialog.SetApiKey("")
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetApiKey(apiKey)

        self.settingsDialog.SetUseIncludesFile(True)
        self.settingsDialog.SetIncludesFile("")
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetUseIncludesFile(False)

        self.settingsDialog.SetUseExcludesFile(True)
        self.settingsDialog.SetExcludesFile("")
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetUseExcludesFile(False)

        # Test validation with invalid scheduled time
        # (in the past).
        self.settingsDialog.SetScheduleType("Once")
        scheduledTime = \
            datetime.time(datetime.now().replace(microsecond=0) -
                          timedelta(minutes=1))
        self.settingsDialog.SetScheduledTime(scheduledTime)
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetScheduleType("Manually")

        # Test settings dialog validation with MyTardis URL which
        # responds with a redirect (302):
        myTardisUrl = self.settingsDialog.GetMyTardisUrl()
        self.settingsDialog.SetMyTardisUrl("%s/redirect" % myTardisUrl)
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetMyTardisUrl(myTardisUrl)

        # Test settings dialog validation with valid settings.
        # Tick the ignore old datasets checkbox and the
        # validate folder structure checkbox, so that we
        # get a summary of how many datasets were found
        # within that time period.
        self.settingsDialog.SetIgnoreOldDatasets(True)
        self.settingsDialog.SetIgnoreOldDatasetIntervalNumber(6)
        self.settingsDialog.SetIgnoreOldDatasetIntervalUnit("months")
        self.settingsDialog.SetValidateFolderStructure(True)
        PostEvent(settingsDialogValidationEvent)

        # Test updating autostart file:
        self.settingsModel.UpdateAutostartFile()

        # Test renaming instrument to an available instrument name:
        renameInstrumentEvent = MYDATA_EVENTS.RenameInstrumentEvent(
            settingsDialog=self.settingsDialog,
            settingsModel=self.settingsModel,
            facilityName=self.settingsDialog.GetFacilityName(),
            oldInstrumentName=self.settingsDialog.GetInstrumentName(),
            newInstrumentName="Renamed Instrument")
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

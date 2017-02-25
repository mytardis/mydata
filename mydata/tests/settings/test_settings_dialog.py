"""
Test ability to open settings dialog and save fields.
"""
from datetime import datetime
from datetime import timedelta
import os
import tempfile
import unittest

import wx

from ...models.settings import SettingsModel
from ...models.settings.serialize import SaveSettingsToDisk
from ...models.settings.serialize import SaveFieldsFromDialog
from ...utils.autostart import UpdateAutostartFile
from ...views.settings import SettingsDialog
from ...events import MYDATA_EVENTS
from ...events import PostEvent
from ...events import RenameInstrument
from ...utils.exceptions import DuplicateKey
from ..utils import StartFakeMyTardisServer
from ..utils import WaitForFakeMyTardisServerToStart


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
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = \
            SettingsModel(configPath=configPath, checkForUpdates=False)
        self.tempConfig = tempfile.NamedTemporaryFile()
        self.tempFilePath = self.tempConfig.name
        self.tempConfig.close()
        self.settingsModel.configPath = self.tempFilePath
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.settingsModel.general.myTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset"))
        self.assertTrue(os.path.exists(dataDirectory))
        self.settingsModel.general.dataDirectory = dataDirectory
        SaveSettingsToDisk(self.settingsModel)
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

        # Simulate browsing for data directory:
        dataDirectory = self.settingsDialog.GetDataDirectory()
        pyCommandEvent = wx.PyCommandEvent()
        self.settingsDialog.OnBrowse(pyCommandEvent)
        self.settingsDialog.SetDataDirectory(dataDirectory)

        # Test the explicit enabling of paste in the API Key field
        # for wxMac (which disables cut/copy/paste in password
        # fields as a security precaution).
        apiKey = self.settingsDialog.GetApiKey()
        self.settingsDialog.apiKeyField.SetFocus()
        self.settingsDialog.OnSelectAll(pyCommandEvent)
        self.settingsDialog.OnPaste(pyCommandEvent)
        self.settingsDialog.SetApiKey(apiKey)

        # Select folder structures to test OnSelectFolderStructure:
        for folderStructure in self.settingsDialog.folderStructures:
            self.settingsDialog.SetFolderStructure(folderStructure)
            self.settingsDialog.OnSelectFolderStructure(event=None)

        # Simulate clicking Ignore Old Datasets checkbox:
        self.settingsDialog.SetIgnoreOldDatasets(True)
        self.settingsDialog.OnIgnoreOldDatasetsCheckBox(pyCommandEvent)
        self.settingsDialog.SetIgnoreOldDatasets(False)
        self.settingsDialog.OnIgnoreOldDatasetsCheckBox(pyCommandEvent)

        # Simulate clicking Ignore Old Datasets spin control
        # Different event handling for singular or plural / zero.
        self.settingsDialog.SetIgnoreOldDatasetIntervalNumber(1)
        self.settingsDialog.OnIgnoreOldDatasetsSpinCtrl(pyCommandEvent)
        self.settingsDialog.SetIgnoreOldDatasetIntervalNumber(0)
        self.settingsDialog.OnIgnoreOldDatasetsSpinCtrl(pyCommandEvent)

        # Simulate clicking Ignore New Files checkbox:
        self.settingsDialog.SetIgnoreNewFiles(True)
        self.settingsDialog.OnIgnoreNewFilesCheckBox(pyCommandEvent)
        self.settingsDialog.SetIgnoreNewFiles(False)
        self.settingsDialog.OnIgnoreNewFilesCheckBox(pyCommandEvent)

        # Simulate clicking Ignore New Files spin control
        # Different event handling for singular or plural / zero.
        self.settingsDialog.SetIgnoreNewFilesMinutes(1)
        self.settingsDialog.OnIgnoreNewFilesSpinCtrl(pyCommandEvent)
        self.settingsDialog.SetIgnoreNewFilesMinutes(0)
        self.settingsDialog.OnIgnoreNewFilesSpinCtrl(pyCommandEvent)

        # Simulate browsing for includes file:
        self.settingsDialog.OnBrowseIncludesFile(pyCommandEvent)

        # Simulate browsing for excludes file:
        self.settingsDialog.OnBrowseExcludesFile(pyCommandEvent)

        # Start fake MyTardis server to test settings dialog validation:
        WaitForFakeMyTardisServerToStart(self.settingsModel.general.myTardisUrl)

        # Test settings dialog validation with invalid settings,
        # which will prompt a suggestion, based on which facilities
        # the user has access to (as a facility manager).
        # When running unittests, suggestions are automatically applied.
        facilityName = self.settingsDialog.GetFacilityName()
        self.settingsDialog.SetFacilityName("")
        settingsDialogValidationEvent = \
            MYDATA_EVENTS.SettingsDialogValidationEvent(
                settingsDialog=self.settingsDialog,
                settingsModel=self.settingsModel)
        PostEvent(settingsDialogValidationEvent)
        self.settingsDialog.SetFacilityName(facilityName)

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

        # Test incrementing and decrementing dates and times.
        self.settingsDialog.OnIncrementDate(pyCommandEvent)
        self.settingsDialog.OnDecrementDate(pyCommandEvent)
        self.settingsDialog.OnIncrementTime(pyCommandEvent)
        self.settingsDialog.OnDecrementTime(pyCommandEvent)
        self.settingsDialog.OnIncrementFromTime(pyCommandEvent)
        self.settingsDialog.OnDecrementFromTime(pyCommandEvent)
        self.settingsDialog.OnIncrementToTime(pyCommandEvent)
        self.settingsDialog.OnDecrementToTime(pyCommandEvent)

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
        self.settingsModel.advanced.startAutomaticallyOnLogin = True
        UpdateAutostartFile(self.settingsModel)
        self.settingsModel.advanced.startAutomaticallyOnLogin = False
        UpdateAutostartFile(self.settingsModel)

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
        SaveFieldsFromDialog(self.settingsModel, self.settingsDialog,
                             configPath=self.tempFilePath, saveToDisk=True)
        # Test dragging and dropping a MyData.cfg onto settings dialog:
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "testdata/testdataUsernameDataset.cfg")
        self.settingsDialog.SetLocked(False)
        self.settingsDialog.OnDropFiles([configPath])
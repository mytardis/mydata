"""
Test ability to validate settings.
"""
import unittest
import tempfile
import os
import sys

from mydata.models.settings import SettingsModel
from mydata.models.settings.serialize import SaveSettingsToDisk
import mydata.models.settings.validation
from mydata.models.settings.validation import ValidateSettings
from mydata.utils.exceptions import InvalidSettings
from mydata.tests.utils import StartFakeMyTardisServer
from mydata.tests.utils import WaitForFakeMyTardisServerToStart


class SettingsValidationTester(unittest.TestCase):
    """
    Test ability to validate settings.
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, *args, **kwargs):
        super(SettingsValidationTester, self).__init__(*args, **kwargs)
        self.httpd = None
        self.fakeMyTardisHost = "127.0.0.1"
        self.fakeMyTardisPort = None
        self.fakeMyTardisServerThread = None
        self.settingsModel = None
        self.tempConfig = None
        self.tempFilePath = None

    def setUp(self):
        """
        If we're creating a wx application in the test, it's
        safest to do it in setUp, because we know that setUp
        will only be called once, so only one app will be created.
        """
        configPath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata/testdataUsernameDataset_POST.cfg")
        self.assertTrue(os.path.exists(configPath))
        self.settingsModel = SettingsModel(configPath=configPath,
                                           checkForUpdates=False)
        self.tempConfig = tempfile.NamedTemporaryFile()
        self.tempFilePath = self.tempConfig.name
        self.tempConfig.close()
        self.settingsModel.configPath = self.tempFilePath
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        dataDirectory = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata", "testdataUsernameDataset"))
        self.assertTrue(os.path.exists(dataDirectory))
        self.settingsModel.general.dataDirectory = dataDirectory
        SaveSettingsToDisk(self.settingsModel)

    def tearDown(self):
        if os.path.exists(self.tempFilePath):
            os.remove(self.tempFilePath)
        self.httpd.shutdown()
        self.fakeMyTardisServerThread.join()

    def test_settings_validation(self):
        """
        Test ability to validate settings.
        """
        # pylint: disable=too-many-statements

        # Wait for fake MyTardis server to start:
        WaitForFakeMyTardisServerToStart(
            self.settingsModel.general.myTardisUrl)

        # Let's populate some settings which will trigger warnings
        # when using MyData's Test Run feature:
        self.settingsModel.filters.ignoreOldDatasets = True
        self.settingsModel.filters.ignoreNewFiles = True
        self.settingsModel.filters.userFilter = "*"
        self.settingsModel.filters.datasetFilter = "*"
        self.settingsModel.filters.experimentFilter = "*"
        self.settingsModel.advanced.uploadInvalidUserOrGroupFolders = False
        folderStructure = self.settingsModel.advanced.folderStructure
        self.assertEqual(folderStructure, 'Username / Dataset')
        ValidateSettings(self.settingsModel, testRun=True)
        self.settingsModel.advanced.folderStructure = 'User Group / Dataset'
        ValidateSettings(self.settingsModel, testRun=True)
        self.settingsModel.advanced.folderStructure = folderStructure

        # Now let's make some settings invalid and test validation:

        # Test missing MyTardis URL.
        self.settingsModel.general.myTardisUrl = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")

        # Test invalid MyTardis URL:
        self.settingsModel.general.myTardisUrl = "invalid://tardis.url"
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl

        # Test invalid HTTP status code from MyTardis URL:
        self.settingsModel.general.myTardisUrl = \
            "%s/request/http/code/401" % self.fakeMyTardisUrl
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl

        # Test invalid HTTP status code from MyTardis URL:
        self.settingsModel.general.myTardisUrl = \
            "%s/request/http/code/500" % self.fakeMyTardisUrl
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl

        # Simulate timeout while trying to access MyTardis URL:
        timeout = mydata.models.settings.validation.DEFAULT_TIMEOUT
        mydata.models.settings.validation.DEFAULT_TIMEOUT = \
            sys.float_info.epsilon
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")
        mydata.models.settings.validation.DEFAULT_TIMEOUT = timeout

        # Simulate ConnectionError while trying to access MyTardis URL:
        self.settingsModel.general.myTardisUrl = \
            "%s/request/connectionerror/" % self.fakeMyTardisUrl
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl

        # Now we need to restart the fake MyTardis server, because
        # our last test asked it to shut down abruptly, simulating
        # a connection error:
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        self.settingsModel.general.myTardisUrl = self.fakeMyTardisUrl
        WaitForFakeMyTardisServerToStart(self.fakeMyTardisUrl)

        # Test missing Facility Name:
        self.settingsModel.general.facilityName = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "facility_name")
        self.settingsModel.general.facilityName = "Test Facility"

        # Test invalid Facility Name:
        self.settingsModel.general.facilityName = "Invalid Facility"
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "facility_name")
        self.settingsModel.general.facilityName = "Test Facility"

        # Test another invalid Facility Name:
        # This simulates a bug leading to ValidateSettings attempting
        # to validate a non-string as though it were a string.
        # A logged exception and a failed settings validation is better
        # than having the GUI become unresponsive.
        self.settingsModel.general.facilityName = 12345  # pylint: disable=redefined-variable-type
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        # With this type of exception, ValidateSettings can't be expected
        # to provide the invalid field name - it's just a catch all
        # exception:
        self.assertEqual(invalidSettings.field, "")
        self.settingsModel.general.facilityName = "Test Facility"

        # Test missing Instrument Name:
        self.settingsModel.general.instrumentName = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "instrument_name")
        self.settingsModel.general.instrumentName = "Test Instrument"

        # Test missing Contact Name:
        self.settingsModel.general.contactName = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "contact_name")
        self.settingsModel.general.contactName = "Test User"

        # Test missing Contact Email:
        self.settingsModel.general.contactEmail = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "contact_email")
        self.settingsModel.general.contactEmail = "testuser@example.com"

        # Test invalid Contact Email:
        self.settingsModel.general.contactEmail = "invalid.email_address"
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "contact_email")
        self.settingsModel.general.contactEmail = "testuser@example.com"

        # Test invalid data directory:
        dataDirectory = self.settingsModel.general.dataDirectory
        self.settingsModel.general.dataDirectory = "/invalid/path"
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "data_directory")
        self.settingsModel.general.dataDirectory = dataDirectory

        # Test missing MyTardis Username:
        self.settingsModel.general.username = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "username")
        self.settingsModel.general.username = "testfacility"

        # Test missing MyTardis API Key:
        self.settingsModel.general.apiKey = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "api_key")
        self.settingsModel.general.apiKey = "????????"

        # Test invalid MyTardis API Key:
        self.settingsModel.general.apiKey = "invalid"
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        # Settings validation doesn't know whether it's the username
        # or API key which is wrong when authentication fails:
        self.assertEqual(invalidSettings.field, "username")
        self.settingsModel.general.apiKey = "????????"

        # Test globs validations for valid includes file:
        includesFileObj = tempfile.NamedTemporaryFile()
        includesFilePath = includesFileObj.name
        includesFileObj.close()
        with open(includesFilePath, 'w') as includesFile:
            includesFile.write("*.tif\n")
        self.settingsModel.filters.useIncludesFile = True
        self.settingsModel.filters.includesFile = includesFilePath
        ValidateSettings(self.settingsModel, testRun=True)
        os.remove(includesFilePath)

        # Test globs validation for non-existent includes file:
        self.settingsModel.filters.useIncludesFile = True
        self.settingsModel.filters.includesFile = ("/path/doesn't/exist")
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "includes_file")

        # Test globs validation for includes file path which is
        # actually a directory:
        self.settingsModel.filters.useIncludesFile = True
        self.settingsModel.filters.includesFile = os.getcwd()
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "includes_file")

        # Test globs validation for includes file path which is
        # actually a binary file:
        includesFilePath = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata",
            "testdataDataset/Flowers/Pond_Water_Hyacinth_Flowers.jpg"))
        self.settingsModel.filters.useIncludesFile = True
        self.settingsModel.filters.includesFile = includesFilePath
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception

        # Test globs validation where checkbox is ticked for using
        # an includes file, but no includes file is specified:
        self.settingsModel.filters.useIncludesFile = True
        self.settingsModel.filters.includesFile = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings(self.settingsModel)
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "includes_file")

        # Test "Test Run" warnings triggered when use_includes_file
        # and/or use_excludes_file are activated.  The warning should
        # appear in STDERR output of this test.
        self.settingsModel.filters.useIncludesFile = True
        includesFileObj = tempfile.NamedTemporaryFile()
        includesFilePath = includesFileObj.name
        includesFileObj.close()
        with open(includesFilePath, 'w') as includesFile:
            includesFile.write("*.tif\n")
        self.settingsModel.filters.includesFile = includesFilePath
        self.settingsModel.filters.useExcludesFile = True
        excludesFileObj = tempfile.NamedTemporaryFile()
        excludesFilePath = excludesFileObj.name
        excludesFileObj.close()
        with open(excludesFilePath, 'w') as excludesFile:
            excludesFile.write("*.tif\n")
        self.settingsModel.filters.excludesFile = excludesFilePath
        ValidateSettings(self.settingsModel, testRun=True)

        # Test "Test Run" warnings triggered when use_includes_file
        # and/or use_excludes_file are activated.  The warning should
        # appear in STDERR output of this test.
        self.settingsModel.filters.useIncludesFile = False
        self.settingsModel.filters.useExcludesFile = True
        ValidateSettings(self.settingsModel, testRun=True)

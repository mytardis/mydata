"""
Test ability to validate settings.
"""
import os
import sys
import tempfile

import mydata.models.settings.validation
from ...settings import SETTINGS
from ...models.settings.validation import ValidateSettings
from ...utils.exceptions import InvalidSettings
from ..utils import StartFakeMyTardisServer
from ..utils import WaitForFakeMyTardisServerToStart
from .. import MyDataSettingsTester


class SettingsValidationTester(MyDataSettingsTester):
    """
    Test ability to validate settings.
    """
    def setUp(self):
        """
        If we're creating a wx application in the test, it's
        safest to do it in setUp, because we know that setUp
        will only be called once, so only one app will be created.
        """
        super(SettingsValidationTester, self).setUp()
        self.UpdateSettingsFromCfg(
            "testdataUsernameDataset_POST",
            dataFolderName="testdataUsernameDataset")

    def test_settings_validation(self):
        """
        Test ability to validate settings.
        """
        # pylint: disable=too-many-statements

        # Let's populate some settings which will trigger warnings
        # when using MyData's Test Run feature:
        SETTINGS.filters.ignoreOldDatasets = True
        SETTINGS.filters.ignoreNewFiles = True
        SETTINGS.filters.userFilter = "*"
        SETTINGS.filters.datasetFilter = "*"
        SETTINGS.filters.experimentFilter = "*"
        SETTINGS.advanced.uploadInvalidUserOrGroupFolders = False
        folderStructure = SETTINGS.advanced.folderStructure
        self.assertEqual(folderStructure, 'Username / Dataset')
        ValidateSettings(testRun=True)
        SETTINGS.advanced.folderStructure = 'User Group / Dataset'
        ValidateSettings(testRun=True)
        SETTINGS.advanced.folderStructure = folderStructure

        # Now let's make some settings invalid and test validation:

        # Test missing MyTardis URL.
        SETTINGS.general.myTardisUrl = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")

        # Test invalid MyTardis URL:
        SETTINGS.general.myTardisUrl = "invalid://tardis.url"
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl

        # Test invalid HTTP status code from MyTardis URL:
        SETTINGS.general.myTardisUrl = \
            "%s/request/http/code/401" % self.fakeMyTardisUrl
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl

        # Test invalid HTTP status code from MyTardis URL:
        SETTINGS.general.myTardisUrl = \
            "%s/request/http/code/500" % self.fakeMyTardisUrl
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl

        # Simulate timeout while trying to access MyTardis URL:
        timeout = mydata.models.settings.validation.DEFAULT_TIMEOUT
        mydata.models.settings.validation.DEFAULT_TIMEOUT = \
            sys.float_info.epsilon
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")
        mydata.models.settings.validation.DEFAULT_TIMEOUT = timeout

        # Simulate ConnectionError while trying to access MyTardis URL:
        sys.stderr.write(
            "\n*** Asking fake MyTardis server to shut down abruptly...\n\n")
        SETTINGS.general.myTardisUrl = \
            "%s/request/connectionerror/" % self.fakeMyTardisUrl
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "mytardis_url")
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl

        # Now we need to restart the fake MyTardis server, because
        # our last test asked it to shut down abruptly, simulating
        # a connection error:
        self.fakeMyTardisHost, self.fakeMyTardisPort, self.httpd, \
            self.fakeMyTardisServerThread = StartFakeMyTardisServer()
        self.fakeMyTardisUrl = \
            "http://%s:%s" % (self.fakeMyTardisHost, self.fakeMyTardisPort)
        SETTINGS.general.myTardisUrl = self.fakeMyTardisUrl
        WaitForFakeMyTardisServerToStart(self.fakeMyTardisUrl)

        # Test missing Facility Name:
        SETTINGS.general.facilityName = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "facility_name")
        SETTINGS.general.facilityName = "Test Facility"

        # Test invalid Facility Name:
        SETTINGS.general.facilityName = "Invalid Facility"
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "facility_name")
        SETTINGS.general.facilityName = "Test Facility"

        # Test another invalid Facility Name:
        # This simulates a bug leading to ValidateSettings attempting
        # to validate a non-string as though it were a string.
        # A logged exception and a failed settings validation is better
        # than having the GUI become unresponsive.
        SETTINGS.general.facilityName = 12345  # pylint: disable=redefined-variable-type
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        # With this type of exception, ValidateSettings can't be expected
        # to provide the invalid field name - it's just a catch all
        # exception:
        self.assertEqual(invalidSettings.field, "")
        SETTINGS.general.facilityName = "Test Facility"

        # Test missing Instrument Name:
        SETTINGS.general.instrumentName = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "instrument_name")
        SETTINGS.general.instrumentName = "Test Instrument"

        # Test missing Contact Name:
        SETTINGS.general.contactName = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "contact_name")
        SETTINGS.general.contactName = "Test User"

        # Test missing Contact Email:
        SETTINGS.general.contactEmail = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "contact_email")
        SETTINGS.general.contactEmail = "testuser@example.com"

        # Test invalid Contact Email:
        SETTINGS.general.contactEmail = "invalid.email_address"
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "contact_email")
        SETTINGS.general.contactEmail = "testuser@example.com"

        # Test invalid data directory:
        dataDirectory = SETTINGS.general.dataDirectory
        SETTINGS.general.dataDirectory = "/invalid/path"
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "data_directory")
        SETTINGS.general.dataDirectory = dataDirectory

        # Test missing MyTardis Username:
        SETTINGS.general.username = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "username")
        SETTINGS.general.username = "testfacility"

        # Test missing MyTardis API Key:
        SETTINGS.general.apiKey = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "api_key")
        SETTINGS.general.apiKey = "????????"

        # Test invalid MyTardis API Key:
        SETTINGS.general.apiKey = "invalid"
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        # Settings validation doesn't know whether it's the username
        # or API key which is wrong when authentication fails:
        self.assertEqual(invalidSettings.field, "username")
        SETTINGS.general.apiKey = "????????"

        # Test globs validations for valid includes file:
        includesFileObj = tempfile.NamedTemporaryFile()
        includesFilePath = includesFileObj.name
        includesFileObj.close()
        with open(includesFilePath, 'w') as includesFile:
            includesFile.write("*.tif\n")
        SETTINGS.filters.useIncludesFile = True
        SETTINGS.filters.includesFile = includesFilePath
        ValidateSettings(testRun=True)
        os.remove(includesFilePath)

        # Test globs validation for non-existent includes file:
        SETTINGS.filters.useIncludesFile = True
        SETTINGS.filters.includesFile = ("/path/doesn't/exist")
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "includes_file")

        # Test globs validation for includes file path which is
        # actually a directory:
        SETTINGS.filters.useIncludesFile = True
        SETTINGS.filters.includesFile = os.getcwd()
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "includes_file")

        # Test globs validation for includes file path which is
        # actually a binary file:
        includesFilePath = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../testdata",
            "testdataDataset/Flowers/Pond_Water_Hyacinth_Flowers.jpg"))
        SETTINGS.filters.useIncludesFile = True
        SETTINGS.filters.includesFile = includesFilePath
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception

        # Test globs validation where checkbox is ticked for using
        # an includes file, but no includes file is specified:
        SETTINGS.filters.useIncludesFile = True
        SETTINGS.filters.includesFile = ""
        with self.assertRaises(InvalidSettings) as contextManager:
            ValidateSettings()
        invalidSettings = contextManager.exception
        self.assertEqual(invalidSettings.field, "includes_file")

        # Test "Test Run" warnings triggered when use_includes_file
        # and/or use_excludes_file are activated.  The warning should
        # appear in STDERR output of this test.
        SETTINGS.filters.useIncludesFile = True
        includesFileObj = tempfile.NamedTemporaryFile()
        includesFilePath = includesFileObj.name
        includesFileObj.close()
        with open(includesFilePath, 'w') as includesFile:
            includesFile.write("*.tif\n")
        SETTINGS.filters.includesFile = includesFilePath
        SETTINGS.filters.useExcludesFile = True
        excludesFileObj = tempfile.NamedTemporaryFile()
        excludesFilePath = excludesFileObj.name
        excludesFileObj.close()
        with open(excludesFilePath, 'w') as excludesFile:
            excludesFile.write("*.tif\n")
        SETTINGS.filters.excludesFile = excludesFilePath
        ValidateSettings(testRun=True)

        # Test "Test Run" warnings triggered when use_includes_file
        # and/or use_excludes_file are activated.  The warning should
        # appear in STDERR output of this test.
        SETTINGS.filters.useIncludesFile = False
        SETTINGS.filters.useExcludesFile = True
        ValidateSettings(testRun=True)

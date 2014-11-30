import sys
import sqlite3
import requests
import traceback
import os
from ConfigParser import ConfigParser
from validate_email import validate_email

from logger.Logger import logger
from UserModel import UserModel
from FacilityModel import FacilityModel
from InstrumentModel import InstrumentModel
from Exceptions import DuplicateKey
from Exceptions import Unauthorized


class SettingsModel():
    class SettingsValidation():
        def __init__(self, valid, message="", field="", suggestion=None):
            self.valid = valid
            self.message = message
            self.field = field
            self.suggestion = suggestion

        def GetValid(self):
            return self.valid

        def GetMessage(self):
            return self.message

        def GetField(self):
            return self.field

        def GetSuggestion(self):
            return self.suggestion

    def __init__(self, mydataConfigPath=None, sqlitedb=None):
        self.mydataConfigPath = mydataConfigPath
        self.sqlitedb = sqlitedb

        self.instrument_name = ""
        self.instrument = None
        self.facility_name = ""
        self.facility = None
        self.contact_name = ""
        self.contact_email = ""
        self.data_directory = ""
        self.mytardis_url = ""
        self.username = ""
        self.api_key = ""

        self.background_mode = "False"

        self.uploaderModel = None
        self.uploadToStagingRequest = None
        self.sshKeyPair = None

        self.validation = self.SettingsValidation(True)

        if self.mydataConfigPath is not None and \
                os.path.exists(self.mydataConfigPath):
            logger.info("Reading settings from: " + self.mydataConfigPath)
            try:
                configParser = ConfigParser()
                configParser.read(self.mydataConfigPath)
                configFileSection = "MyData"
                self.instrument_name = configParser.get(configFileSection,
                                                        "instrument_name", "")
                self.facility_name = configParser.get(configFileSection,
                                                      "facility_name", "")
                self.data_directory = configParser.get(configFileSection,
                                                       "data_directory", "")
                self.contact_name = configParser.get(configFileSection,
                                                     "contact_name", "")
                self.contact_email = configParser.get(configFileSection,
                                                      "contact_email", "")
                self.mytardis_url = configParser.get(configFileSection,
                                                     "mytardis_url", "")
                self.username = configParser.get(configFileSection,
                                                 "username", "")
                self.api_key = configParser.get(configFileSection,
                                                "api_key", "")
            except:
                logger.error(traceback.format_exc())
        elif self.sqlitedb is not None:
            logger.info("Reading settings from: " + self.sqlitedb)
            conn = sqlite3.connect(self.sqlitedb)
            with conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS " +
                               "settings(id integer primary key," +
                               "field text,value text)")

                cursor.execute("SELECT value FROM settings " +
                               "WHERE field='instrument_name'")
                rows = cursor.fetchall()
                if len(rows) > 0:
                    self.instrument_name = rows[0]['value']
                else:
                    self.instrument_name = ""

                cursor.execute("SELECT value FROM settings " +
                               "WHERE field='facility_name'")
                rows = cursor.fetchall()
                if len(rows) > 0:
                    self.facility_name = rows[0]['value']
                else:
                    self.facility_name = ""

                cursor.execute("SELECT value FROM settings " +
                               "WHERE field='contact_name'")
                rows = cursor.fetchall()
                if len(rows) > 0:
                    self.contact_name = rows[0]['value']
                else:
                    self.contact_name = ""

                cursor.execute("SELECT value FROM settings " +
                               "WHERE field='contact_email'")
                rows = cursor.fetchall()
                if len(rows) > 0:
                    self.contact_email = rows[0]['value']
                else:
                    self.contact_email = ""

                cursor.execute("SELECT value FROM settings " +
                               "WHERE field='data_directory'")
                rows = cursor.fetchall()
                if len(rows) > 0:
                    self.data_directory = rows[0]['value']
                else:
                    self.data_directory = ""

                cursor.execute("SELECT value FROM settings " +
                               "WHERE field='mytardis_url'")
                rows = cursor.fetchall()
                if len(rows) > 0:
                    self.mytardis_url = rows[0]['value']
                else:
                    self.mytardis_url = ""

                cursor.execute("SELECT value FROM settings " +
                               "WHERE field='username'")
                rows = cursor.fetchall()
                if len(rows) > 0:
                    self.username = rows[0]['value']
                else:
                    self.username = ""

                cursor.execute("SELECT value FROM settings " +
                               "WHERE field='api_key'")
                rows = cursor.fetchall()
                if len(rows) > 0:
                    self.api_key = rows[0]['value']
                else:
                    self.api_key = ""

                cursor.execute("SELECT value FROM settings " +
                               "WHERE field='background_mode'")
                rows = cursor.fetchall()
                if len(rows) > 0:
                    self.background_mode = rows[0]['value']
                else:
                    self.background_mode = "False"

    def GetInstrument(self):
        if self.instrument is None:
            self.instrument = \
                InstrumentModel.GetInstrument(self,
                                              self.GetFacility(),
                                              self.GetInstrumentName())
        return self.instrument

    def GetInstrumentName(self):
        return self.instrument_name

    def GetInstrument(self):
        return self.instrument

    def SetInstrumentName(self, instrumentName):
        self.instrument_name = instrumentName

    def GetFacilityName(self):
        return self.facility_name

    def GetFacility(self):
        return self.facility

    def SetFacilityName(self, facilityName):
        self.facility_name = facilityName

    def GetContactName(self):
        return self.contact_name

    def SetContactName(self, contactName):
        self.contact_name = contactName

    def GetContactEmail(self):
        return self.contact_email

    def SetContactEmail(self, contactEmail):
        self.contact_email = contactEmail

    def GetDataDirectory(self):
        return self.data_directory

    def SetDataDirectory(self, dataDirectory):
        self.data_directory = dataDirectory

    def GetMyTardisUrl(self):
        return self.mytardis_url

    def SetMyTardisUrl(self, myTardisUrl):
        self.mytardis_url = myTardisUrl

    def GetUsername(self):
        return self.username

    def SetUsername(self, username):
        self.username = username

    def GetApiKey(self):
        return self.api_key

    def SetApiKey(self, apiKey):
        self.api_key = apiKey

    def RunningInBackgroundMode(self):
        return self.background_mode

    def SetBackgroundMode(self, backgroundMode):
        self.background_mode = backgroundMode

    def GetUploadToStagingRequest(self):
        return self.uploadToStagingRequest

    def SetUploadToStagingRequest(self, uploadToStagingRequest):
        self.uploadToStagingRequest = uploadToStagingRequest

    def GetUploaderModel(self):
        return self.uploaderModel

    def SetUploaderModel(self, uploaderModel):
        self.uploaderModel = uploaderModel

    def GetSshKeyPair(self):
        return self.sshKeyPair

    def SetSshKeyPair(self, sshKeyPair):
        self.sshKeyPair = sshKeyPair

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def SaveToDisk(self):
        if self.mydataConfigPath is None:
            raise Exception("SettingsModel.SaveToDisk called "
                            "with mydataConfigPath == None.")

        configParser = ConfigParser()
        with open(self.mydataConfigPath, 'w') as configFile:
            configParser.add_section("MyData")
            configParser.set("MyData", "instrument_name",
                             self.GetInstrumentName())
            configParser.set("MyData", "facility_name",
                             self.GetFacilityName())
            configParser.set("MyData", "mytardis_url",
                             self.GetMyTardisUrl())
            configParser.set("MyData", "contact_name",
                             self.GetContactName())
            configParser.set("MyData", "contact_email",
                             self.GetContactEmail())
            configParser.set("MyData", "data_directory",
                             self.GetDataDirectory())
            configParser.set("MyData", "username",
                             self.GetUsername())
            configParser.set("MyData", "api_key",
                             self.GetApiKey())
            configParser.write(configFile)

        logger.info("Saved settings to " + self.mydataConfigPath)

    def SaveFieldsFromDialog(self, settingsDialog):
        self.SetInstrumentName(settingsDialog.GetInstrumentName())
        self.SetFacilityName(settingsDialog.GetFacilityName())
        self.SetMyTardisUrl(settingsDialog.GetMyTardisUrl())
        self.SetContactName(settingsDialog.GetContactName())
        self.SetContactEmail(settingsDialog.GetContactEmail())
        self.SetDataDirectory(settingsDialog.GetDataDirectory())
        self.SetUsername(settingsDialog.GetUsername())
        self.SetApiKey(settingsDialog.GetApiKey())
        if self.sqlitedb is not None:
            self.SaveToDisk()

    def Validate(self):
        try:
            if self.GetInstrumentName().strip() == "":
                message = "Please enter a valid instrument name."
                self.validation = self.SettingsValidation(False, message,
                                                          "instrument_name")
                return self.validation
            if self.GetDataDirectory().strip() == "":
                message = "Please enter a valid data directory."
                self.validation = self.SettingsValidation(False, message,
                                                          "data_directory")
                return self.validation
            if self.GetMyTardisUrl().strip() == "":
                message = "Please enter a valid MyTardis URL, " \
                    "beginning with \"http://\" or \"https://\"."
                self.validation = self.SettingsValidation(False, message,
                                                          "mytardis_url")
                return self.validation
            if self.GetContactName().strip() == "":
                message = "Please enter a valid contact name."
                self.validation = self.SettingsValidation(False, message,
                                                          "contact_name")
                return self.validation
            if self.GetContactEmail().strip() == "":
                message = "Please enter a valid contact email."
                self.validation = self.SettingsValidation(False, message,
                                                          "contact_email")
                return self.validation
            if self.GetUsername().strip() == "":
                message = "Please enter a MyTardis username."
                self.validation = self.SettingsValidation(False, message,
                                                          "username")
                return self.validation
            if self.GetApiKey().strip() == "":
                message = "Please enter your MyTardis API key.\n\n" \
                    "To find your API key, log into MyTardis using the " \
                    "account you wish to use with MyData (\"%s\"), " \
                    "click on your username (in the upper-right corner), " \
                    "and select \"Download Api Key\" from the drop-down " \
                    "menu.  If \"Download Api Key\" is missing from the " \
                    "drop-down menu, please contact your MyTardis " \
                    "administrator.\n\n" \
                    "Open the downloaded file (\"<username>.key\") in " \
                    "Notepad (or a suitable text editor).  Its content "\
                    "will appear as follows:\n\n" \
                    "    ApiKey <username>:<API key>\n\n" \
                    "Copy the <API key> (after the colon) to your clipboard, " \
                    "and paste it into MyData's \"MyTardis API Key\" field." \
                    % self.GetUsername().strip()
                self.validation = self.SettingsValidation(False, message,
                                                          "api_key")
                return self.validation
            if not os.path.exists(self.GetDataDirectory()):
                message = "The data directory: \"%s\" doesn't exist!" % \
                    self.GetDataDirectory()
                self.validation = self.SettingsValidation(False, message,
                                                          "data_directory")
                return self.validation

            try:
                r = requests.get(self.GetMyTardisUrl() + "/about/", timeout=5)
                if r.status_code < 200 or r.status_code >= 300:
                    if not self.GetMyTardisUrl().startswith("http"):
                        message = "Please enter a valid MyTardis URL, " \
                            "beginning with \"http://\" or \"https://\"."
                        suggestion = "http://" + self.GetMyTardisUrl()
                    else:
                        message = "Please enter a valid MyTardis URL.\n\n"
                        message += "Received HTTP status code %d" \
                            % r.status_code
                        suggestion = None
                    self.validation = self.SettingsValidation(False, message,
                                                              "mytardis_url",
                                                              suggestion)
                    return self.validation
                if "MyTardis" not in r.text:
                    if not self.GetMyTardisUrl().startswith("http"):
                        message = "Please enter a valid MyTardis URL, " \
                            "beginning with \"http://\" or \"https://\"."
                        suggestion = "http://" + self.GetMyTardisUrl()
                    else:
                        message = "Please enter a valid MyTardis URL."
                        suggestion = None
                    self.validation = self.SettingsValidation(False, message,
                                                              "mytardis_url",
                                                              suggestion)
                    return self.validation
            except:
                if not self.GetMyTardisUrl().startswith("http"):
                    message = "Please enter a valid MyTardis URL, " \
                        "beginning with \"http://\" or \"https://\"."
                    suggestion = "http://" + self.GetMyTardisUrl()
                else:
                    message = "Please enter a valid MyTardis URL.\n\n"
                    etype, evalue = sys.exc_info()[:2]
                    excOnlyList = \
                        traceback.format_exception_only(etype, evalue)
                    for excOnly in excOnlyList:
                        message += excOnly
                    suggestion = None
                self.validation = self.SettingsValidation(False, message,
                                                          "mytardis_url",
                                                          suggestion)
                logger.error(traceback.format_exc())
                return self.validation

            url = self.GetMyTardisUrl() + \
                "/api/v1/user/?format=json&username=" + self.GetUsername()
            headers = {"Authorization": "ApiKey " + self.GetUsername() + ":" +
                       self.GetApiKey(),
                       "Content-Type": "application/json",
                       "Accept": "application/json"}
            response = requests.get(headers=headers, url=url)
            if response.status_code < 200 or response.status_code >= 300:
                message = "Your MyTardis credentials are invalid.\n\n" \
                    "Please check your Username and API Key."
                self.validation = self.SettingsValidation(False, message,
                                                          "username")
                return self.validation

            if self.GetFacilityName().strip() == "":
                message = "Please enter a valid facility name."
                suggestion = None
                try:
                    defaultUserModel = UserModel\
                        .GetUserRecord(self, self.GetUsername())
                    facilities = FacilityModel\
                        .GetMyFacilities(self, defaultUserModel)
                    if len(facilities) == 1:
                        suggestion = facilities[0].GetName()
                    self.validation = self.SettingsValidation(False, message,
                                                              "facility_name",
                                                              suggestion)
                except:
                    logger.error(traceback.format_exc())
                    self.validation = self.SettingsValidation(False, message,
                                                              "facility_name",
                                                              suggestion)
                    return self.validation
            defaultUserModel = UserModel.GetUserRecord(self,
                                                       self.GetUsername())
            facilities = FacilityModel.GetMyFacilities(self,
                                                       defaultUserModel)
            for f in facilities:
                if self.GetFacilityName() == f.GetName():
                    self.facility = f
                    break
            if self.facility is None:
                message = "Facility \"%s\" was not found in MyTardis." \
                    % self.GetFacilityName()
                if len(facilities) > 0:
                    message += "\n\n" + \
                        "The facilities which user \"%s\" " \
                        "has access to are:\n\n" % self.GetUsername()
                    for f in facilities:
                        message = message + "    " + f.GetName() + "\n"
                else:
                    message += "\n\n" + \
                        "Please ask your MyTardis administrator to " \
                        "ensure that the \"%s\" facility exists and that " \
                        "user \"%s\" is a member of the managers group for " \
                        "that facility." \
                        % (self.GetFacilityName(),
                           self.GetUsername())
                suggestion = None
                if len(facilities) == 1:
                    suggestion = facilities[0].GetName()
                self.validation = self.SettingsValidation(False, message,
                                                          "facility_name",
                                                          suggestion)
                return self.validation

            logger.warning("For now, we are assuming that if we find an "
                           "instrument record with the correct name and "
                           "facility, then it must be the correct instrument "
                           "record to use with this MyData instance. "
                           "However, if the instrument record we find is "
                           "associated with a different uploader instance "
                           "(suggesting a different MyData instance), then "
                           "we really shouldn't reuse the same instrument "
                           "record, unless it is just a case of having "
                           "multiple uploader instances for multiple "
                           "MAC addresses (Ethernet and WiFi) "
                           "on the same instrument PC.")
            self.instrument = \
                InstrumentModel.GetInstrument(self,
                                              self.GetFacility(),
                                              self.GetInstrumentName())
            if self.instrument is None:
                logger.info("No instrument record with name \"%s\" was found "
                            "in facility \"%s\", so we will create one."
                            % (self.GetInstrumentName(),
                               self.GetFacilityName()))
                try:
                    self.instrument = InstrumentModel.CreateInstrument(
                        self, self.GetFacility(), self.GetInstrumentName())
                except Unauthorized, e:
                    message = str(e)
                    self.validation = \
                        self.SettingsValidation(False, message,
                                                "instrument_name")
                    return self.validation
                logger.info("self.instrument = " + str(self.instrument))
            if self.instrument is not None and self.uploaderModel is not None:
                try:
                    self.uploaderModel.SetInstrument(self.instrument)
                except DoesNotExist:
                    logger.error("Tried to SetInstrument in uploader record"
                                 "but uploader record doesn't exist yet.")

            if not validate_email(self.GetContactEmail()):
                message = "Please enter a valid contact email."
                self.validation = self.SettingsValidation(False, message,
                                                          "contact_email")
                return self.validation
        except:
            message = traceback.format_exc()
            self.validation = self.SettingsValidation(False, message, "")
            return self.validation

        return self.SettingsValidation(True)

    def RequiredFieldIsBlank(self):
        return self.GetInstrumentName() == "" or \
            self.GetFacilityName() == "" or \
            self.GetContactName() == "" or \
            self.GetContactEmail() == "" or \
            self.GetDataDirectory() == "" or \
            self.GetMyTardisUrl() == "" or \
            self.GetUsername() == "" or \
            self.GetApiKey() == ""

    def GetValidation(self):
        return self.validation

    def RenameInstrument(self, facilityName,
                         oldInstrumentName, newInstrumentName):
        defaultUserModel = UserModel.GetUserRecord(self, self.GetUsername())
        facilities = FacilityModel.GetMyFacilities(self, defaultUserModel)
        facility = None
        for f in facilities:
            if facilityName == f.GetName():
                facility = f
                break
        if facility is None:
            raise Exception("Facility is None in "
                            "SettingsModel's RenameInstrument.")
        oldInstrument = \
            InstrumentModel.GetInstrument(self, facility, oldInstrumentName)
        if oldInstrument is None:
            raise Exception("Instrument record for old instrument "
                            "name not found in SettingsModel's "
                            "RenameInstrument.")
        newInstrument = \
            InstrumentModel.GetInstrument(self, facility, newInstrumentName)
        if newInstrument is not None:
            raise DuplicateKey(
                message="Instrument with name \"%s\" "
                        "already exists" % newInstrumentName)
        oldInstrument.Rename(newInstrumentName)

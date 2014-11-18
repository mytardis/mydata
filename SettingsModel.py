import sqlite3
import requests
import traceback
import os
from ConfigParser import ConfigParser
from validate_email import validate_email

from logger.Logger import logger
from UserModel import UserModel
from FacilityModel import FacilityModel


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
        self.facility_name = ""
        self.contact_name = ""
        self.contact_email = ""
        self.data_directory = ""
        self.mytardis_url = ""
        self.username = ""
        self.api_key = ""

        self.background_mode = "False"

        self.uploadToStagingRequest = None

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

    def GetInstrumentName(self):
        return self.instrument_name

    def SetInstrumentName(self, instrumentName):
        self.instrument_name = instrumentName

    def GetFacilityName(self):
        return self.facility_name

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
        return self.background_mode == "True"

    def SetBackgroundMode(self, backgroundMode):
        if backgroundMode is True or \
                (backgroundMode is not None and backgroundMode == "True"):
            self.backgroundMode = "True"
        else:
            self.backgroundMode = "False"

    def GetUploadToStagingRequest(self):
        return self.uploadToStagingRequest

    def SetUploadToStagingRequest(self, uploadToStagingRequest):
        self.uploadToStagingRequest = uploadToStagingRequest

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
                message = "Please enter your MyTardis API key."
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
                if r.status_code != 200:
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
                    message = "Please enter a valid MyTardis URL."
                    suggestion = None
                self.validation = self.SettingsValidation(False, message,
                                                          "mytardis_url",
                                                          suggestion)
                return self.validation

            url = self.GetMyTardisUrl() + \
                "/api/v1/user/?format=json&username=" + self.GetUsername()
            headers = {"Authorization": "ApiKey " + self.GetUsername() + ":" +
                       self.GetApiKey(),
                       "Content-Type": "application/json",
                       "Accept": "application/json"}
            response = requests.get(headers=headers, url=url)
            if response.status_code < 200 or response.status_code >= 300:
                message = "Your MyTardis credentials are invalid."
                self.validation = self.SettingsValidation(False, message,
                                                          "username")
                return self.validation

            if self.GetFacilityName().strip() == "":
                message = "Please enter a valid facility name."
                suggestion = None
                try:
                    defaultUserModel = UserModel.GetUserRecord(self,
                                                               self.GetUsername())
                    facilities = FacilityModel.GetMyFacilities(self,
                                                               defaultUserModel)
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
            facilityMatch = None
            for f in facilities:
                if self.GetFacilityName() == f.GetName():
                    facilityMatch = f
                    break
            if facilityMatch is None:
                message = "Facility \"%s\" was not " \
                    "found on MyTardis (or user \"%s\" " \
                    "doesn't have access to it)." % \
                    (self.GetFacilityName(), self.GetUsername())
                if len(facilities) > 0:
                    message = message + "\n\nThe facilities which user \"%s\" " \
                        "has access to are:\n\n" % self.GetUsername()
                    for f in facilities:
                        message = message + "    " + f.GetName() + "\n"
                suggestion = None
                if len(facilities) == 1:
                    suggestion = facilities[0].GetName()
                self.validation = self.SettingsValidation(False, message,
                                                          "facility_name",
                                                          suggestion)
                return self.validation

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

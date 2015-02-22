import sys
import requests
import traceback
import os
from glob import glob
from ConfigParser import ConfigParser
from validate_email import validate_email

from logger.Logger import logger
from UserModel import UserModel
from FacilityModel import FacilityModel
from InstrumentModel import InstrumentModel
from UploaderModel import UploaderModel
from Exceptions import DuplicateKey
from Exceptions import Unauthorized
from Exceptions import IncompatibleMyTardisVersion


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

    def __init__(self, configPath=None):
        self.SetConfigPath(configPath)

        self.instrument_name = ""
        self.instrument = None
        self.facility_name = ""
        self.facility = None
        self.contact_name = ""
        self.contact_email = ""
        self.data_directory = ""
        self.mytardis_url = ""
        self.group_prefix = ""
        self.username = ""
        self.api_key = ""

        self.background_mode = "False"

        self.uploaderModel = None
        self.uploadToStagingRequest = None
        self.sshKeyPair = None

        self.validation = self.SettingsValidation(True)
        self.incompatibleMyTardisVersion = False

        self.LoadSettings()

    def LoadSettings(self, configPath=None):
        if configPath is None:
            configPath = self.GetConfigPath()

        if self.GetConfigPath() is not None and \
                os.path.exists(self.GetConfigPath()):
            logger.info("Reading settings from: " + self.GetConfigPath())
            try:
                configParser = ConfigParser()
                configParser.read(self.GetConfigPath())
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
                self.group_prefix = configParser.get(configFileSection,
                                                     "group_prefix", "")
                self.username = configParser.get(configFileSection,
                                                 "username", "")
                self.api_key = configParser.get(configFileSection,
                                                "api_key", "")
            except:
                logger.error(traceback.format_exc())

    def GetInstrument(self):
        if self.instrument is None:
            self.instrument = \
                InstrumentModel.GetInstrument(self,
                                              self.GetFacility(),
                                              self.GetInstrumentName())
        return self.instrument

    def SetInstrument(self, instrument):
        self.instrument = instrument

    def GetInstrumentName(self):
        return self.instrument_name

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

    def GetGroupPrefix(self):
        return self.group_prefix

    def SetGroupPrefix(self, groupPrefix):
        self.group_prefix = groupPrefix

    def GetUsername(self):
        return self.username

    def SetUsername(self, username):
        self.username = username

    def GetDefaultOwner(self):
        if hasattr(self, "defaultOwner") and \
                self.defaultOwner.GetUsername() == self.GetUsername():
            return self.defaultOwner
        self.defaultOwner = UserModel.GetUserByUsername(self,
                                                        self.GetUsername())
        return self.defaultOwner

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
        if self.uploaderModel is None:
            self.uploaderModel = UploaderModel(self)
        return self.uploaderModel

    def SetUploaderModel(self, uploaderModel):
        self.uploaderModel = uploaderModel

    def GetSshKeyPair(self):
        return self.sshKeyPair

    def SetSshKeyPair(self, sshKeyPair):
        self.sshKeyPair = sshKeyPair

    def IsIncompatibleMyTardisVersion(self):
        return self.incompatibleMyTardisVersion

    def SetIncompatibleMyTardisVersion(self, incompatibleMyTardisVersion):
        self.incompatibleMyTardisVersion = incompatibleMyTardisVersion

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def SaveToDisk(self, configPath=None):
        if configPath is None:
            configPath = self.GetConfigPath()
        if configPath is None:
            raise Exception("SettingsModel.SaveToDisk called "
                            "with configPath == None.")

        configParser = ConfigParser()
        with open(configPath, 'w') as configFile:
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
            configParser.set("MyData", "group_prefix",
                             self.GetGroupPrefix())
            configParser.set("MyData", "username",
                             self.GetUsername())
            configParser.set("MyData", "api_key",
                             self.GetApiKey())
            configParser.write(configFile)

        logger.info("Saved settings to " + configPath)

    def SaveFieldsFromDialog(self, settingsDialog, configPath=None):
        if configPath is None:
            configPath = self.GetConfigPath()
        self.SetInstrumentName(settingsDialog.GetInstrumentName())
        self.SetFacilityName(settingsDialog.GetFacilityName())
        self.SetMyTardisUrl(settingsDialog.GetMyTardisUrl())
        self.SetContactName(settingsDialog.GetContactName())
        self.SetContactEmail(settingsDialog.GetContactEmail())
        self.SetDataDirectory(settingsDialog.GetDataDirectory())
        self.SetGroupPrefix(settingsDialog.GetGroupPrefix())
        self.SetUsername(settingsDialog.GetUsername())
        self.SetApiKey(settingsDialog.GetApiKey())
        # self.mydataConfigPath could be None for the temporary
        # settingsModel created during SettingsDialog's validation.
        if self.GetConfigPath() is not None:
            self.SaveToDisk(self.GetConfigPath())

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
            filesDepth1 = glob(os.path.join(self.GetDataDirectory(), '*'))
            dirsDepth1 = filter(lambda f: os.path.isdir(f), filesDepth1)
            if len(dirsDepth1) == 0:
                message = "The data directory: \"%s\" doesn't contain any " \
                    "user folders!" % \
                    self.GetDataDirectory()
                self.validation = self.SettingsValidation(False, message,
                                                          "data_directory")
                return self.validation
            filesDepth2 = glob(os.path.join(self.GetDataDirectory(), '*', '*'))
            dirsDepth2 = filter(lambda f: os.path.isdir(f), filesDepth2)
            if len(dirsDepth2) == 0:
                message = "The data directory: \"%s\" should contain dataset " \
                    "folders within user folders." % \
                    self.GetDataDirectory()
                self.validation = self.SettingsValidation(False, message,
                                                          "data_directory")
                return self.validation
            print "Number of dirs at depth 2 is %d" % len(dirsDepth2)
            filesDepth3 = glob(os.path.join(self.GetDataDirectory(), '*', '*', '*'))
            dirsDepth3 = filter(lambda f: os.path.isdir(f), filesDepth3)
            print "Number of dirs at depth 3 is %d" % len(dirsDepth3)
            filesDepth4 = glob(os.path.join(self.GetDataDirectory(), '*', '*', '*'))
            dirsDepth4 = filter(lambda f: os.path.isdir(f), filesDepth4)
            print "Number of dirs at depth 4 is %d" % len(dirsDepth4)

            try:
                session = requests.Session()
                r = session.get(self.GetMyTardisUrl() + "/about/")
                status_code = r.status_code
                content = r.text
                history = r.history
                url = r.url
                r.close()
                session.close()
                if status_code < 200 or status_code >= 300:
                    logger.debug("Received HTTP %d while trying to access "
                                 "MyTardis server (%s)."
                                 % (status_code, self.GetMyTardisUrl()))
                    logger.debug(content)
                    if not self.GetMyTardisUrl().startswith("http"):
                        message = "Please enter a valid MyTardis URL, " \
                            "beginning with \"http://\" or \"https://\"."
                        suggestion = "http://" + self.GetMyTardisUrl()
                    else:
                        message = "Please enter a valid MyTardis URL.\n\n"
                        message += "Received HTTP status code %d" \
                            % status_code
                        suggestion = None
                    self.validation = self.SettingsValidation(False, message,
                                                              "mytardis_url",
                                                              suggestion)
                    return self.validation
                elif history:
                    message = "MyData attempted to access MyTardis at " \
                        "\"%s\", but was redirected to:" \
                        "\n\n" % self.GetMyTardisUrl()
                    message += "\t%s" % url
                    message += "\n\n"
                    message += "A redirection could be caused by any of " \
                        "the following reasons:" \
                        "\n\n" \
                        "1. You may be required to log into a web portal " \
                        "before you can access external sites." \
                        "\n\n" \
                        "2. You may be required to access external sites " \
                        "via a proxy server.  This is not supported by " \
                        "MyData at present." \
                        "\n\n" \
                        "3. You might not be using the preferred notation " \
                        "for your MyTardis URL.  If attempting to navigate " \
                        "to this URL in your web browser results in a " \
                        "modified URL appearing in your browser's address " \
                        "bar, but you are sure that the modified URL still " \
                        "represents the MyTardis site you are trying to " \
                        "access, then you should update the MyTardis URL " \
                        "in your MyData settings, so that the MyTardis " \
                        "server doesn't need to modify it." \
                        "\n\n" \
                        "4. Someone could have hijacked your MyTardis site " \
                        "and could be redirecting you to a malicious site. " \
                        "If you suspect this, please contact your MyTardis " \
                        "administrator immediately."
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
                    logger.debug(traceback.format_exc())
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
            session = requests.Session()
            response = session.get(headers=headers, url=url)
            # Consume response content, so session will be closed.
            content = response.text
            status_code = response.status_code
            response.close()
            session.close()
            if status_code < 200 or status_code >= 300:
                message = "Your MyTardis credentials are invalid.\n\n" \
                    "Please check your Username and API Key."
                self.validation = self.SettingsValidation(False, message,
                                                          "username")
                return self.validation

            if self.GetFacilityName().strip() == "":
                message = "Please enter a valid facility name."
                suggestion = None
                try:
                    defaultUserModel = self.GetDefaultOwner()
                    facilities = FacilityModel\
                        .GetMyFacilities(self, defaultUserModel)
                    if len(facilities) == 1:
                        suggestion = facilities[0].GetName()
                    self.validation = self.SettingsValidation(False, message,
                                                              "facility_name",
                                                              suggestion)
                    return self.validation
                except:
                    logger.error(traceback.format_exc())
                    self.validation = self.SettingsValidation(False, message,
                                                              "facility_name",
                                                              suggestion)
                    return self.validation
            defaultUserModel = self.GetDefaultOwner()
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
                           "MAC addresses (Ethernet and Wi-Fi) "
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
            logger.debug("Validating email address.")
            if not validate_email(self.GetContactEmail()):
                message = "Please enter a valid contact email."
                self.validation = self.SettingsValidation(False, message,
                                                          "contact_email")
                return self.validation
            logger.debug("Done validating email address.")
        except IncompatibleMyTardisVersion:
            logger.debug("Incompatible MyTardis Version.")
            self.SetIncompatibleMyTardisVersion(True)
            raise
        except:
            message = traceback.format_exc()
            logger.error(message)
            self.validation = self.SettingsValidation(False, message, "")
            return self.validation

        logger.debug("SettingsModel validation succeeded!")
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
        defaultUserModel = self.GetDefaultOwner()
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

    def GetConfigPath(self):
        return self.configPath

    def SetConfigPath(self, configPath):
        self.configPath = configPath

import json
import sys
import requests
import traceback
import subprocess
import os
import psutil
import getpass
from glob import glob
from ConfigParser import ConfigParser
from validate_email import validate_email
from datetime import datetime
from datetime import timedelta
import threading
import tempfile

from mydata.logs import logger
from mydata.models.user import UserModel
from mydata.models.facility import FacilityModel
from mydata.models.instrument import InstrumentModel
from mydata.models.uploader import UploaderModel
from mydata.utils.exceptions import DuplicateKey
from mydata.utils.exceptions import Unauthorized
from mydata.utils.exceptions import IncompatibleMyTardisVersion

defaultStartupInfo = None
defaultCreationFlags = 0
if sys.platform.startswith("win"):
    defaultStartupInfo = subprocess.STARTUPINFO()
    defaultStartupInfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
    defaultStartupInfo.wShowWindow = subprocess.SW_HIDE
    import win32process
    defaultCreationFlags = win32process.CREATE_NO_WINDOW


class LastSettingsUpdateTrigger:
    READ_FROM_DISK = 0
    UI_RESPONSE = 1


class SettingsValidation():
    def __init__(self, valid, message="", field="", suggestion=None,
                 datasetCount=-1):
        self.valid = valid
        self.message = message
        self.field = field
        self.suggestion = suggestion
        self.datasetCount = datasetCount

    def IsValid(self):
        return self.valid

    def GetMessage(self):
        return self.message

    def GetField(self):
        return self.field

    def GetSuggestion(self):
        return self.suggestion

    def GetDatasetCount(self):
        return self.datasetCount


class SettingsModel():
    def __init__(self, configPath):
        self.SetConfigPath(configPath)

        self.uploaderModel = None
        self.uploadToStagingRequest = None
        self.sshKeyPair = None

        self.validation = SettingsValidation(True)
        self.incompatibleMyTardisVersion = False

        self.last_settings_update_trigger = \
            LastSettingsUpdateTrigger.READ_FROM_DISK

        self.connectivityCheckInterval = 30  # seconds

        self.LoadSettings()

    def LoadSettings(self, configPath=None):
        """
        Sets some default values for settings fields, then loads a settings
        file,
        e.g. C:\Users\jsmith\AppData\Local\Monash University\MyData\MyData.cfg
        """
        # General tab
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

        # Schedule tab
        self.schedule_type = "Manually"
        self.monday_checked = False
        self.tuesday_checked = False
        self.wednesday_checked = False
        self.thursday_checked = False
        self.friday_checked = False
        self.saturday_checked = False
        self.sunday_checked = False
        self.scheduled_date = \
            datetime.date(datetime.now())
        self.scheduled_time = \
            datetime.time(datetime.now().replace(microsecond=0) +
                          timedelta(minutes=1))
        self.timer_minutes = 15
        self.timer_from_time = \
            datetime.time(datetime.strptime("12:00 AM", "%I:%M %p"))
        self.timer_to_time = \
            datetime.time(datetime.strptime("11:59 PM", "%I:%M %p"))

        # Filters tab
        self.user_filter = ""
        self.dataset_filter = ""
        self.experiment_filter = ""
        self.ignore_old_datasets = False
        self.ignore_interval_number = 0
        self.ignore_interval_unit = "months"

        # Advanced tab
        self.folder_structure = "Username / Dataset"
        self.dataset_grouping = "Instrument Name - Dataset Owner's Full Name"
        self.group_prefix = ""
        self.max_upload_threads = 5
        self.max_upload_retries = 5
        self.validate_folder_structure = True
        self.start_automatically_on_login = True

        self.locked = False

        self.uuid = None

        if configPath is None:
            configPath = self.GetConfigPath()

        if configPath is not None and os.path.exists(configPath):
            logger.info("Reading settings from: " + configPath)
            try:
                configParser = ConfigParser()
                configParser.read(configPath)
                configFileSection = "MyData"
                fields = ["instrument_name", "facility_name", "data_directory",
                          "contact_name", "contact_email", "mytardis_url",
                          "username", "api_key",
                          "schedule_type", "monday_checked", "tuesday_checked",
                          "wednesday_checked", "thursday_checked",
                          "friday_checked", "saturday_checked",
                          "sunday_checked", "scheduled_date", "scheduled_time",
                          "timer_minutes", "timer_from_time", "timer_to_time",
                          "user_filter", "dataset_filter", "experiment_filter",
                          "folder_structure",
                          "dataset_grouping", "group_prefix",
                          "ignore_interval_unit", "max_upload_threads",
                          "max_upload_retries",
                          "validate_folder_structure", "locked", "uuid",
                          "start_automatically_on_login"]
                for field in fields:
                    if configParser.has_option(configFileSection, field):
                        self.__dict__[field] = \
                            configParser.get(configFileSection, field)
                if configParser.has_option(configFileSection,
                                           "ignore_old_datasets"):
                    self.ignore_old_datasets = \
                        configParser.getboolean(configFileSection,
                                                "ignore_old_datasets")
                if configParser.has_option(configFileSection,
                                           "ignore_interval_number"):
                    self.ignore_interval_number = \
                        configParser.getint(configFileSection,
                                            "ignore_interval_number")
                if configParser.has_option(configFileSection,
                                           "max_upload_threads"):
                    self.max_upload_threads = \
                        configParser.getint(configFileSection,
                                            "max_upload_threads")
                if configParser.has_option(configFileSection,
                                           "max_upload_retries"):
                    self.max_upload_retries = \
                        configParser.getint(configFileSection,
                                            "max_upload_retries")
                if configParser.has_option(configFileSection,
                                           "validate_folder_structure"):
                    self.validate_folder_structure = \
                        configParser.getboolean(configFileSection,
                                                "validate_folder_structure")
                if configParser.has_option(configFileSection,
                                           "start_automatically_on_login"):
                    self.start_automatically_on_login = \
                        configParser.getboolean(configFileSection,
                                                "start_automatically_on_login")
                if configParser.has_option(configFileSection,
                                           "locked"):
                    self.locked = configParser.getboolean(configFileSection,
                                                          "locked")
                if configParser.has_option(configFileSection,
                                           "scheduled_date"):
                    datestring = configParser.get(configFileSection,
                                                  "scheduled_date")
                    self.scheduled_date = \
                        datetime.date(datetime.strptime(datestring,
                                                        "%Y-%m-%d"))
                if configParser.has_option(configFileSection,
                                           "scheduled_time"):
                    timestring = configParser.get(configFileSection,
                                                  "scheduled_time")
                    self.scheduled_time = datetime.strptime(timestring,
                                                            "%H:%M:%S")
                    self.scheduled_time = datetime.time(self.scheduled_time)
                if self.schedule_type == "Timer":
                    if configParser.has_option(configFileSection,
                                               "timer_minutes"):
                        self.timer_minutes = \
                            configParser.getint(configFileSection,
                                                "timer_minutes")
                    if configParser.has_option(configFileSection,
                                               "timer_from_time"):
                        timestring = configParser.get(configFileSection,
                                                      "timer_from_time")
                        self.timer_from_time = datetime.strptime(timestring,
                                                                 "%H:%M:%S")
                        self.timer_from_time = \
                            datetime.time(self.timer_from_time)
                    if configParser.has_option(configFileSection,
                                               "timer_to_time"):
                        timestring = configParser.get(configFileSection,
                                                      "timer_to_time")
                        self.timer_to_time = datetime.strptime(timestring,
                                                               "%H:%M:%S")
                    self.timer_to_time = datetime.time(self.timer_to_time)
                else:
                    self.timer_minutes = 15
                    self.timer_from_time = \
                        datetime.time(datetime.strptime("12:00 AM",
                                                        "%I:%M %p"))
                    self.timer_to_time = \
                        datetime.time(datetime.strptime("11:59 PM",
                                                        "%I:%M %p"))
                if self.schedule_type == "Weekly":
                    for day in ["monday_checked", "tuesday_checked",
                                "wednesday_checked", "thursday_checked",
                                "friday_checked", "saturday_checked",
                                "sunday_checked"]:
                        if configParser.has_option(configFileSection, day):
                            self.__dict__[day] = \
                                configParser.getboolean(configFileSection, day)
                else:
                    self.monday_checked = False
                    self.tuesday_checked = False
                    self.wednesday_checked = False
                    self.thursday_checked = False
                    self.friday_checked = False
                    self.saturday_checked = False
                    self.sunday_checked = False
            except:
                logger.error(traceback.format_exc())

        self.last_settings_update_trigger = \
            LastSettingsUpdateTrigger.READ_FROM_DISK

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
        if not self.facility:
            try:
                facilities = FacilityModel.GetMyFacilities(self)
                for f in facilities:
                    if self.GetFacilityName() == f.GetName():
                        self.facility = f
                        break
            except:
                logger.error(traceback.format_exc())
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
        self.mytardis_url = myTardisUrl.rstrip('/')

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

    def GetScheduleType(self):
        return self.schedule_type

    def SetScheduleType(self, scheduleType):
        self.schedule_type = scheduleType

    def IsMondayChecked(self):
        return self.monday_checked

    def SetMondayChecked(self, checked):
        self.monday_checked = checked

    def IsTuesdayChecked(self):
        return self.tuesday_checked

    def SetTuesdayChecked(self, checked):
        self.tuesday_checked = checked

    def IsWednesdayChecked(self):
        return self.wednesday_checked

    def SetWednesdayChecked(self, checked):
        self.wednesday_checked = checked

    def IsThursdayChecked(self):
        return self.thursday_checked

    def SetThursdayChecked(self, checked):
        self.thursday_checked = checked

    def IsFridayChecked(self):
        return self.friday_checked

    def SetFridayChecked(self, checked):
        self.friday_checked = checked

    def IsSaturdayChecked(self):
        return self.saturday_checked

    def SetSaturdayChecked(self, checked):
        self.saturday_checked = checked

    def IsSundayChecked(self):
        return self.sunday_checked

    def SetSundayChecked(self, checked):
        self.sunday_checked = checked

    def GetScheduledDate(self):
        return self.scheduled_date

    def SetScheduledDate(self, scheduledDate):
        self.scheduled_date = scheduledDate

    def GetScheduledTime(self):
        return self.scheduled_time

    def SetScheduledTime(self, scheduledTime):
        self.scheduled_time = scheduledTime

    def GetTimerMinutes(self):
        return self.timer_minutes

    def SetTimerMinutes(self, timerMinutes):
        self.timer_minutes = timerMinutes

    def GetTimerFromTime(self):
        return self.timer_from_time

    def SetTimerFromTime(self, timerFromTime):
        self.timer_from_time = timerFromTime

    def GetTimerToTime(self):
        return self.timer_to_time

    def SetTimerToTime(self, timerToTime):
        self.timer_to_time = timerToTime

    def GetFolderStructure(self):
        return self.folder_structure

    def SetFolderStructure(self, folderStructure):
        self.folder_structure = folderStructure

    def AlertUserAboutMissingFolders(self):
        return False

    def ValidateFolderStructure(self):
        return self.validate_folder_structure

    def SetValidateFolderStructure(self, validateFolderStructure):
        self.validate_folder_structure = validateFolderStructure

    def StartAutomaticallyOnLogin(self):
        return self.start_automatically_on_login

    def SetStartAutomaticallyOnLogin(self, startAutomaticallyOnLogin):
        self.start_automatically_on_login = startAutomaticallyOnLogin

    def Locked(self):
        return self.locked

    def SetLocked(self, locked):
        self.locked = locked

    def GetDatasetGrouping(self):
        return self.dataset_grouping

    def SetDatasetGrouping(self, datasetGrouping):
        self.dataset_grouping = datasetGrouping

    def GetGroupPrefix(self):
        return self.group_prefix

    def SetGroupPrefix(self, groupPrefix):
        self.group_prefix = groupPrefix

    def GetUserFilter(self):
        return self.user_filter

    def SetUserFilter(self, userFilter):
        self.user_filter = userFilter

    def GetDatasetFilter(self):
        return self.dataset_filter

    def SetDatasetFilter(self, datasetFilter):
        self.dataset_filter = datasetFilter

    def GetExperimentFilter(self):
        return self.experiment_filter

    def SetExperimentFilter(self, experimentFilter):
        self.experiment_filter = experimentFilter

    def IgnoreOldDatasets(self):
        return self.ignore_old_datasets

    def SetIgnoreOldDatasets(self, ignoreOldDatasets):
        self.ignore_old_datasets = ignoreOldDatasets

    def GetIgnoreOldDatasetIntervalNumber(self):
        return self.ignore_interval_number

    def SetIgnoreOldDatasetIntervalNumber(self,
                                          ignoreOldDatasetIntervalNumber):
        self.ignore_interval_number = ignoreOldDatasetIntervalNumber

    def GetIgnoreOldDatasetIntervalUnit(self):
        return self.ignore_interval_unit

    def SetIgnoreOldDatasetIntervalUnit(self, ignoreOldDatasetIntervalUnit):
        self.ignore_interval_unit = ignoreOldDatasetIntervalUnit

    def GetMaxUploadThreads(self):
        return self.max_upload_threads

    def SetMaxUploadThreads(self, maxUploadThreads):
        self.max_upload_threads = maxUploadThreads

    def GetMaxUploadRetries(self):
        return self.max_upload_retries

    def SetMaxUploadRetries(self, maxUploadRetries):
        self.max_upload_retries = maxUploadRetries

    def GetUuid(self):
        return self.uuid

    def SetUuid(self, uuid):
        self.uuid = uuid

    def GetUploadToStagingRequest(self):
        return self.uploadToStagingRequest

    def SetUploadToStagingRequest(self, uploadToStagingRequest):
        self.uploadToStagingRequest = uploadToStagingRequest

    def GetUploaderModel(self):
        if not self.uploaderModel:
            """
            This could be called from multiple threads simultaneously,
            so it requires locking.
            """
            if not hasattr(self, "createUploaderThreadingLock"):
                self.createUploaderThreadingLock = threading.Lock()
            if self.createUploaderThreadingLock.acquire():
                try:
                    self.uploaderModel = UploaderModel(self)
                finally:
                    self.createUploaderThreadingLock.release()
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
            fields = ["instrument_name", "facility_name", "data_directory",
                      "contact_name", "contact_email", "mytardis_url",
                      "username", "api_key",
                      "schedule_type", "monday_checked", "tuesday_checked",
                      "wednesday_checked", "thursday_checked",
                      "friday_checked", "saturday_checked",
                      "sunday_checked", "scheduled_date", "scheduled_time",
                      "timer_minutes", "timer_from_time", "timer_to_time",
                      "user_filter", "dataset_filter", "experiment_filter",
                      "folder_structure",
                      "dataset_grouping", "group_prefix",
                      "ignore_old_datasets", "ignore_interval_number",
                      "ignore_interval_unit", "max_upload_threads",
                      "max_upload_retries",
                      "validate_folder_structure", "locked", "uuid",
                      "start_automatically_on_login"]
            for field in fields:
                configParser.set("MyData", field, self.__dict__[field])
            configParser.write(configFile)
        logger.info("Saved settings to " + configPath)

    def SaveFieldsFromDialog(self, settingsDialog, configPath=None,
                             saveToDisk=True):
        if configPath is None:
            configPath = self.GetConfigPath()
        # General tab
        self.SetInstrumentName(settingsDialog.GetInstrumentName())
        self.SetFacilityName(settingsDialog.GetFacilityName())
        self.SetMyTardisUrl(settingsDialog.GetMyTardisUrl())
        self.SetContactName(settingsDialog.GetContactName())
        self.SetContactEmail(settingsDialog.GetContactEmail())
        self.SetDataDirectory(settingsDialog.GetDataDirectory())
        self.SetUsername(settingsDialog.GetUsername())
        self.SetApiKey(settingsDialog.GetApiKey())

        # Schedule tab
        self.SetScheduleType(settingsDialog.GetScheduleType())
        self.SetMondayChecked(settingsDialog.IsMondayChecked())
        self.SetTuesdayChecked(settingsDialog.IsTuesdayChecked())
        self.SetWednesdayChecked(settingsDialog.IsWednesdayChecked())
        self.SetThursdayChecked(settingsDialog.IsThursdayChecked())
        self.SetFridayChecked(settingsDialog.IsFridayChecked())
        self.SetSaturdayChecked(settingsDialog.IsSaturdayChecked())
        self.SetSundayChecked(settingsDialog.IsSundayChecked())
        self.SetScheduledDate(settingsDialog.GetScheduledDate())
        self.SetScheduledTime(settingsDialog.GetScheduledTime())
        self.SetTimerMinutes(settingsDialog.GetTimerMinutes())
        self.SetTimerFromTime(settingsDialog.GetTimerFromTime())
        self.SetTimerToTime(settingsDialog.GetTimerToTime())

        # Filters tab
        self.SetUserFilter(settingsDialog.GetUserFilter())
        self.SetDatasetFilter(settingsDialog.GetDatasetFilter())
        self.SetExperimentFilter(settingsDialog.GetExperimentFilter())
        self.SetIgnoreOldDatasets(settingsDialog.IgnoreOldDatasets())
        self.SetIgnoreOldDatasetIntervalNumber(
            settingsDialog.GetIgnoreOldDatasetIntervalNumber())
        self.SetIgnoreOldDatasetIntervalUnit(
            settingsDialog.GetIgnoreOldDatasetIntervalUnit())
        self.SetMaxUploadThreads(settingsDialog.GetMaxUploadThreads())
        self.SetMaxUploadRetries(settingsDialog.GetMaxUploadRetries())

        # Advanced tab
        self.SetFolderStructure(settingsDialog.GetFolderStructure())
        self.SetDatasetGrouping(settingsDialog.GetDatasetGrouping())
        self.SetGroupPrefix(settingsDialog.GetGroupPrefix())
        self.SetValidateFolderStructure(
            settingsDialog.ValidateFolderStructure())
        self.SetStartAutomaticallyOnLogin(
            settingsDialog.StartAutomaticallyOnLogin())

        self.SetLocked(settingsDialog.Locked())

        if saveToDisk:
            self.SaveToDisk(configPath)

        self.last_settings_update_trigger = \
            LastSettingsUpdateTrigger.UI_RESPONSE

    def Validate(self, SetStatusMessage=None):
        datasetCount = -1
        try:
            if self.GetInstrumentName().strip() == "":
                message = "Please enter a valid instrument name."
                self.validation = SettingsValidation(False, message,
                                                     "instrument_name")
                return self.validation
            if self.GetDataDirectory().strip() == "":
                message = "Please enter a valid data directory."
                self.validation = SettingsValidation(False, message,
                                                     "data_directory")
                return self.validation
            if self.GetMyTardisUrl().strip() == "":
                message = "Please enter a valid MyTardis URL, " \
                    "beginning with \"http://\" or \"https://\"."
                self.validation = SettingsValidation(False, message,
                                                     "mytardis_url")
                return self.validation
            if self.GetContactName().strip() == "":
                message = "Please enter a valid contact name."
                self.validation = SettingsValidation(False, message,
                                                     "contact_name")
                return self.validation
            if self.GetContactEmail().strip() == "":
                message = "Please enter a valid contact email."
                self.validation = SettingsValidation(False, message,
                                                     "contact_email")
                return self.validation
            if self.GetUsername().strip() == "":
                message = "Please enter a MyTardis username."
                self.validation = SettingsValidation(False, message,
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
                    "Copy the <API key> (after the colon) to your clipboard," \
                    " and paste it into MyData's \"MyTardis API Key\" field." \
                    % self.GetUsername().strip()
                self.validation = SettingsValidation(False, message,
                                                     "api_key")
                return self.validation
            if not os.path.exists(self.GetDataDirectory()):
                message = "The data directory: \"%s\" doesn't exist!" % \
                    self.GetDataDirectory()
                self.validation = SettingsValidation(False, message,
                                                     "data_directory")
                return self.validation

            if self.ValidateFolderStructure():
                if SetStatusMessage:
                    SetStatusMessage(
                        "Settings validation - checking folder structure...")
                self.validation = self.PerformFolderStructureValidation()
                if not self.validation.IsValid():
                    return self.validation
                datasetCount = self.validation.GetDatasetCount()

            try:
                if SetStatusMessage:
                    SetStatusMessage(
                        "Settings validation - checking MyTardis URL...")
                session = requests.Session()
                r = session.get(self.GetMyTardisUrl() + "/about/", timeout=5)
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
                    self.validation = SettingsValidation(False, message,
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
                    self.validation = SettingsValidation(False, message,
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
                self.validation = SettingsValidation(False, message,
                                                     "mytardis_url",
                                                     suggestion)
                logger.error(traceback.format_exc())
                return self.validation

            """
            Here we perform a rather arbitrary query, just to test
            whether our MyTardis credentials work OK with the API.
            """
            if SetStatusMessage:
                SetStatusMessage(
                     "Settings validation - checking MyTardis credentials...")
            url = self.GetMyTardisUrl() + \
                "/api/v1/user/?format=json&username=" + self.GetUsername()
            headers = {"Authorization": "ApiKey " + self.GetUsername() + ":" +
                       self.GetApiKey(),
                       "Content-Type": "application/json",
                       "Accept": "application/json"}
            response = requests.get(headers=headers, url=url)
            status_code = response.status_code
            # We don't care about the response content here, only the
            # status code, but failing to read the content risks leaving
            # a lingering open connection, so we'll close it.
            response.close()

            def invalid_user():
                message = "Your MyTardis credentials are invalid.\n\n" \
                    "Please check your Username and API Key."
                self.validation = \
                    SettingsValidation(False, message, "username")
                return self.validation

            if status_code < 200 or status_code >= 300:
                return invalid_user()

            if SetStatusMessage:
                SetStatusMessage(
                    "Settings validation - checking MyTardis facility...")
            if self.GetFacilityName().strip() == "":
                message = "Please enter a valid facility name."
                suggestion = None
                try:
                    defaultUserModel = self.GetDefaultOwner()
                    facilities = FacilityModel.GetMyFacilities(self)
                    if len(facilities) == 1:
                        suggestion = facilities[0].GetName()
                    self.validation = SettingsValidation(False, message,
                                                         "facility_name")
                    return self.validation
                except:
                    logger.error(traceback.format_exc())
                    self.validation = SettingsValidation(False, message,
                                                         "facility_name")
                    return self.validation
            defaultUserModel = self.GetDefaultOwner()
            facilities = FacilityModel.GetMyFacilities(self)
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
                self.validation = SettingsValidation(False, message,
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
                           "record.")
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
                        SettingsValidation(False, message, "instrument_name")
                    return self.validation
                logger.info("self.instrument = " + str(self.instrument))
            logger.debug("Validating email address.")
            if not validate_email(self.GetContactEmail()):
                message = "Please enter a valid contact email."
                self.validation = \
                    SettingsValidation(False, message, "contact_email")
                return self.validation
            logger.debug("Done validating email address.")
            if self.GetFolderStructure().startswith('Email'):
                dataDir = self.GetDataDirectory()
                folderNames = os.walk(dataDir).next()[1]
                for folderName in folderNames:
                    if not validate_email(folderName):
                        message = "Folder name \"%s\" in \"%s\" is not a " \
                            "valid email address." % (folderName, dataDir)
                        self.validation = \
                            SettingsValidation(False, message,
                                               "data_directory")
                        return self.validation

            if SetStatusMessage:
                SetStatusMessage(
                    "Settings validation - "
                    "checking if MyData is set to start automatically...")
            logger.warning("This auto-start on login stuff shouldn't really "
                           "be in settings validation.  I just put it here "
                           "temporarily to ensure it doesn't run in the "
                           "main thread.")
            if sys.platform.startswith("win"):
                # Check for MyData shortcut(s) in startup folder(s).

                with tempfile.NamedTemporaryFile(suffix='.vbs', delete=False) \
                        as vbScript:
                    script = r"""
set objShell = CreateObject("WScript.Shell")
startupFolder = objShell.SpecialFolders("Startup")
path = startupFolder & "\" & "MyData.lnk"

Set fso = CreateObject("Scripting.FileSystemObject")
If (fso.FileExists(path)) Then
   msg = path & " exists."
   Wscript.Echo(msg)
   Wscript.Quit(0)
Else
   msg = path & " doesn't exist."
   Wscript.Echo(msg)
   Wscript.Quit(1)
End If
                    """
                    vbScript.write(script)
                cmd = ['cscript', '//Nologo', vbScript.name]
                logger.info("Checking for MyData shortcut in user "
                            "startup items.")
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, shell=False,
                                        startupinfo=defaultStartupInfo,
                                        creationflags=defaultCreationFlags)
                output, _ = proc.communicate()
                shortcutInStartupItems = (proc.returncode == 0)
                if shortcutInStartupItems:
                    logger.info("Found MyData shortcut in user startup items.")
                else:
                    logger.info("Didn't find MyData shortcut in user "
                                "startup items.")
                try:
                    os.unlink(vbScript.name)
                except:
                    logger.error(traceback.format_exc())
                with tempfile.NamedTemporaryFile(suffix='.vbs', delete=False) \
                        as vbScript:
                    script = script.replace("Startup", "AllUsersStartup")
                    vbScript.write(script)
                cmd = ['cscript', '//Nologo', vbScript.name]
                logger.info("Checking for MyData shortcut in common "
                            "startup items.")
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, shell=False,
                                        startupinfo=defaultStartupInfo,
                                        creationflags=defaultCreationFlags)
                output, _ = proc.communicate()
                shortcutInCommonStartupItems = (proc.returncode == 0)
                if shortcutInCommonStartupItems:
                    logger.info("Found MyData shortcut in common "
                                "startup items.")
                else:
                    logger.info("Didn't find MyData shortcut in common "
                                "startup items.")
                try:
                    os.unlink(vbScript.name)
                except:
                    logger.error(traceback.format_exc())
                if (shortcutInStartupItems or shortcutInCommonStartupItems) \
                        and self.StartAutomaticallyOnLogin():
                    logger.info("MyData is already set to start automatically "
                                "on login.")
                elif (not shortcutInStartupItems and
                      not shortcutInCommonStartupItems) and \
                        self.StartAutomaticallyOnLogin():
                    logger.info("Adding MyData shortcut to startup items.")
                    pathToMyDataExe = \
                        r"C:\Program Files (x86)\MyData\MyData.exe"
                    if hasattr(sys, "frozen"):
                        pathToMyDataExe = os.path.realpath(r'.\MyData.exe')
                    with tempfile.NamedTemporaryFile(suffix='.vbs',
                                                     delete=False) as vbScript:
                        script = r"""
Set oWS = WScript.CreateObject("WScript.Shell")
startupFolder = oWS.SpecialFolders("Startup")
sLinkFile = startupFolder & "\" & "MyData.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "%s"
oLink.Save
                        """ % pathToMyDataExe
                        vbScript.write(script)
                    cmd = ['cscript', '//Nologo', vbScript.name]
                    logger.info("Adding MyData shortcut to user "
                                "startup items.")
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                            shell=False,
                                            startupinfo=defaultStartupInfo,
                                            creationflags=defaultCreationFlags)
                    output, _ = proc.communicate()
                    success = (proc.returncode == 0)
                    if not success:
                        logger.error(output)
                    try:
                        os.unlink(vbScript.name)
                    except:
                        logger.error(traceback.format_exc())
                elif (shortcutInStartupItems or
                      shortcutInCommonStartupItems) and \
                        not self.StartAutomaticallyOnLogin():
                    logger.info("Removing MyData from login items.")
                    with tempfile.NamedTemporaryFile(suffix='.vbs',
                                                     delete=False) as vbScript:
                        script = r"""
Set oWS = WScript.CreateObject("WScript.Shell")
Set oFS = CreateObject("Scripting.FileSystemObject")
startupFolder = oWS.SpecialFolders("Startup")
sLinkFile = startupFolder & "\" & "MyData.lnk"
oFS.DeleteFile sLinkFile
                        """
                        vbScript.write(script)
                    cmd = ['cscript', '//Nologo', vbScript.name]
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                            shell=False,
                                            startupinfo=defaultStartupInfo,
                                            creationflags=defaultCreationFlags)
                    output, _ = proc.communicate()
                    success = (proc.returncode == 0)
                    if not success:
                        logger.error(output)
                    try:
                        os.unlink(vbScript.name)
                    except:
                        logger.error(traceback.format_exc())

            elif sys.platform.startswith("darwin"):
                # Update ~/Library/Preferences/com.apple.loginitems.plist
                # cfprefsd can cause unwanted caching.
                # It will automatically respawn when needed.
                for proc in psutil.process_iter():
                    if proc.name() == "cfprefsd" and \
                            proc.username() == getpass.getuser():
                        proc.kill()
                applescript = \
                    'tell application "System Events" ' \
                    'to get the name of every login item'
                cmd = "osascript -e '%s'" % applescript
                loginItemsString = subprocess.check_output(cmd, shell=True)
                loginItems = [item.strip() for item in
                              loginItemsString.split(',')]
                logger.info("Current login items: " + str(loginItems))
                if 'MyData' in loginItems and self.StartAutomaticallyOnLogin():
                    logger.info("MyData is already set to start automatically "
                                "on login.")
                elif 'MyData' not in loginItems and \
                        self.StartAutomaticallyOnLogin():
                    logger.info("Adding MyData to login items.")
                    pathToMyDataApp = "/Applications/MyData.app"
                    if hasattr(sys, "frozen"):
                        # Working directory in py2app bundle is
                        # MyData.app/Contents/Resources/
                        pathToMyDataApp = os.path.realpath('../..')
                    applescript = \
                        'tell application "System Events" ' \
                        'to make login item at end with properties ' \
                        '{path:"%s", hidden:false}' % pathToMyDataApp
                    cmd = "osascript -e '%s'" % applescript
                    returncode = subprocess.call(cmd, shell=True)
                elif 'MyData' in loginItems and \
                        not self.StartAutomaticallyOnLogin():
                    logger.info("Removing MyData from login items.")
                    applescript = \
                        'tell application "System Events" to ' \
                        'delete login item "MyData"'
                    cmd = "osascript -e '%s'" % applescript
                    returncode = subprocess.call(cmd, shell=True)
        except IncompatibleMyTardisVersion:
            logger.debug("Incompatible MyTardis Version.")
            self.SetIncompatibleMyTardisVersion(True)
            raise
        except:
            message = traceback.format_exc()
            logger.error(message)
            self.validation = SettingsValidation(False, message, "")
            return self.validation

        if self.GetScheduleType() == "Once":
            dateTime = datetime.combine(self.GetScheduledDate(),
                                        self.GetScheduledTime())
            if dateTime < datetime.now():
                message = "Scheduled time is in the past."
                self.validation = \
                    SettingsValidation(False, message,
                                       "scheduled_time")
                return

        if SetStatusMessage:
            SetStatusMessage(
                "Settings validation - succeeded!")
        logger.debug("SettingsModel validation succeeded!")
        self.validation = SettingsValidation(True, datasetCount=datasetCount)
        return self.validation

    def PerformFolderStructureValidation(self):
        datasetCount = -1
        userOrGroupFilterString = "*%s*" % self.GetUserFilter()
        datasetFilterString = "*%s*" % self.GetDatasetFilter()
        expFilterString = "*%s*" % self.GetExperimentFilter()
        filesDepth1 = glob(os.path.join(self.GetDataDirectory(),
                           userOrGroupFilterString))
        dirsDepth1 = filter(lambda f: os.path.isdir(f), filesDepth1)
        if len(dirsDepth1) == 0:
            message = "The data directory: \"%s\" doesn't contain any " \
                % self.GetDataDirectory()
            if self.GetFolderStructure() == 'Username / Dataset':
                message += "user folders!"
            elif self.GetFolderStructure() == \
                    'Username / Experiment / Dataset':
                message += "user folders!"
            elif self.GetFolderStructure() == 'Email / Dataset':
                message += "email folders!"
            elif self.GetFolderStructure() == \
                    'Email / Experiment / Dataset':
                message += "email folders!"
            elif self.GetFolderStructure() == \
                    'Username / "MyTardis" / Experiment / Dataset':
                message += "user folders!"
            elif self.GetFolderStructure() == \
                    'User Group / Instrument / Full Name / Dataset':
                message += "user group folders!"
            if self.AlertUserAboutMissingFolders():
                self.validation = SettingsValidation(False, message,
                                                     "data_directory")
                return self.validation
            else:
                logger.warning(message)
        if self.GetFolderStructure() == \
                'User Group / Instrument / Full Name / Dataset':
            filesDepth2 = glob(os.path.join(self.GetDataDirectory(),
                                            userOrGroupFilterString,
                                            self.GetInstrumentName()))
        else:
            filterString = '*'
            if self.GetFolderStructure() == 'Username / Dataset':
                filterString = datasetFilterString
            elif self.GetFolderStructure() == 'Email / Dataset':
                filterString = datasetFilterString
            elif self.GetFolderStructure() == \
                    'Username / Experiment / Dataset':
                filterString = expFilterString
            elif self.GetFolderStructure() == \
                    'Email / Experiment / Dataset':
                filterString = expFilterString
            filesDepth2 = glob(os.path.join(self.GetDataDirectory(),
                                            userOrGroupFilterString,
                                            filterString))
        dirsDepth2 = filter(lambda f: os.path.isdir(f), filesDepth2)
        if len(dirsDepth2) == 0:
            if self.GetFolderStructure() == 'Username / Dataset':
                message = "The data directory: \"%s\" should contain " \
                    "dataset folders within user folders." % \
                    self.GetDataDirectory()
            elif self.GetFolderStructure() == 'Email / Dataset':
                message = "The data directory: \"%s\" should contain " \
                    "dataset folders within email folders." % \
                    self.GetDataDirectory()
            elif self.GetFolderStructure() == \
                    'Username / Experiment / Dataset':
                message = "The data directory: \"%s\" should contain " \
                    "experiment folders within user folders." % \
                    self.GetDataDirectory()
            elif self.GetFolderStructure() == \
                    'Email / Experiment / Dataset':
                message = "The data directory: \"%s\" should contain " \
                    "experiment folders within email folders." % \
                    self.GetDataDirectory()
            elif self.GetFolderStructure() == \
                    'Username / "MyTardis" / Experiment / Dataset':
                message = "Each user folder should contain a " \
                    "\"MyTardis\" folder."
            elif self.GetFolderStructure() == \
                    'User Group / Instrument / Full Name / Dataset':
                message = "Each user group folder should contain an " \
                    "instrument name folder."
            if self.AlertUserAboutMissingFolders():
                self.validation = SettingsValidation(False, message,
                                                     "data_directory")
                return self.validation
            else:
                logger.warning(message)

        if self.GetFolderStructure() == \
                'Username / "MyTardis" / Experiment / Dataset':
            for folderName in dirsDepth2:
                folderName = os.path.basename(folderName)
                if folderName.lower() != 'mytardis':
                    message = "A folder name of \"%s\" was found where " \
                        "a \"MyTardis\" folder was expected." \
                        % folderName
                    self.validation = \
                        SettingsValidation(False, message, "data_directory")
                    return self.validation

        seconds = {}
        seconds['day'] = 24 * 60 * 60
        seconds['week'] = 7 * seconds['day']
        seconds['year'] = int(365.25 * seconds['day'])
        seconds['month'] = seconds['year'] / 12
        singularIgnoreIntervalUnit = self.ignore_interval_unit.rstrip('s')
        ignoreIntervalUnitSeconds = seconds[singularIgnoreIntervalUnit]
        ignoreIntervalSeconds = \
            self.ignore_interval_number * ignoreIntervalUnitSeconds

        if self.GetFolderStructure() == 'Username / Dataset' or \
                self.GetFolderStructure() == 'Email / Dataset':
            if self.IgnoreOldDatasets():
                datasetCount = 0
                for folder in dirsDepth2:
                    ctimestamp = os.path.getctime(folder)
                    ctime = datetime.fromtimestamp(ctimestamp)
                    age = datetime.now() - ctime
                    if age.total_seconds() <= ignoreIntervalSeconds:
                        datasetCount += 1
            else:
                datasetCount = len(dirsDepth2)

        if self.GetFolderStructure() == \
                'User Group / Instrument / Full Name / Dataset':
            filesDepth3 = glob(os.path.join(self.GetDataDirectory(),
                                            userOrGroupFilterString,
                                            self.GetInstrumentName(),
                                            '*'))
        else:
            if self.GetFolderStructure() == 'Username / Dataset':
                filterString1 = datasetFilterString
                filterString2 = '*'
            elif self.GetFolderStructure() == 'Email / Dataset':
                filterString1 = datasetFilterString
                filterString2 = '*'
            elif self.GetFolderStructure() == \
                    'Username / Experiment / Dataset':
                filterString1 = expFilterString
                filterString2 = datasetFilterString
            elif self.GetFolderStructure() == \
                    'Email / Experiment / Dataset':
                filterString1 = expFilterString
                filterString2 = datasetFilterString
            filesDepth3 = glob(os.path.join(self.GetDataDirectory(),
                                            userOrGroupFilterString,
                                            filterString1,
                                            filterString2))
        dirsDepth3 = filter(lambda f: os.path.isdir(f), filesDepth3)
        if len(dirsDepth3) == 0:
            if self.GetFolderStructure() == \
                    'Username / "MyTardis" / Experiment / Dataset':
                message = "Each \"MyTardis\" folder should contain at " \
                    "least one experiment folder."
                if self.AlertUserAboutMissingFolders():
                    self.validation = \
                        SettingsValidation(False, message, "data_directory")
                    return self.validation
                else:
                    logger.warning(message)
            elif self.GetFolderStructure() == \
                    'Username / Experiment / Dataset':
                message = "Each experiment folder should contain at " \
                    "least one dataset folder."
                if self.AlertUserAboutMissingFolders():
                    self.validation = \
                        SettingsValidation(False, message, "data_directory")
                    return self.validation
                else:
                    logger.warning(message)
            elif self.GetFolderStructure() == \
                    'Email / Experiment / Dataset':
                message = "Each experiment folder should contain at " \
                    "least one dataset folder."
                if self.AlertUserAboutMissingFolders():
                    self.validation = \
                        SettingsValidation(False, message, "data_directory")
                    return self.validation
                else:
                    logger.warning(message)
            elif self.GetFolderStructure() == \
                    'User Group / Instrument / Full Name / Dataset':
                message = "Each instrument folder should contain at " \
                    "least one full name (dataset group) folder."
                if self.AlertUserAboutMissingFolders():
                    self.validation = \
                        SettingsValidation(False, message, "data_directory")
                    return self.validation
                else:
                    logger.warning(message)

        if self.GetFolderStructure() == \
                'Username / Experiment / Dataset' or \
                self.GetFolderStructure() == \
                'Email / Experiment / Dataset':
            if self.IgnoreOldDatasets():
                datasetCount = 0
                for folder in dirsDepth3:
                    ctimestamp = os.path.getctime(folder)
                    ctime = datetime.fromtimestamp(ctimestamp)
                    age = datetime.now() - ctime
                    if age.total_seconds() <= ignoreIntervalSeconds:
                        datasetCount += 1
            else:
                datasetCount = len(dirsDepth3)

        if self.GetFolderStructure() == \
                'User Group / Instrument / Full Name / Dataset':
            filesDepth4 = glob(os.path.join(self.GetDataDirectory(),
                                            userOrGroupFilterString,
                                            self.GetInstrumentName(),
                                            '*', datasetFilterString))
        else:
            filesDepth4 = glob(os.path.join(self.GetDataDirectory(),
                                            userOrGroupFilterString,
                                            'MyTardis',
                                            expFilterString,
                                            datasetFilterString))
        dirsDepth4 = filter(lambda f: os.path.isdir(f), filesDepth4)
        if len(dirsDepth4) == 0:
            if self.GetFolderStructure() == \
                    'Username / "MyTardis" / Experiment / Dataset':
                message = "Each experiment folder should contain at " \
                    "least one dataset folder."
                if self.AlertUserAboutMissingFolders():
                    self.validation = \
                        SettingsValidation(False, message, "data_directory")
                    return self.validation
                else:
                    logger.warning(message)
            elif self.GetFolderStructure() == \
                    'User Group / Instrument / Full Name / Dataset':
                message = "Each full name (dataset group) folder " \
                    "should contain at least one dataset folder."
                if self.AlertUserAboutMissingFolders():
                    self.validation = \
                        SettingsValidation(False, message, "data_directory")
                    return self.validation
                else:
                    logger.warning(message)

        if self.GetFolderStructure() == \
                'Username / "MyTardis" / Experiment / Dataset' or \
                self.GetFolderStructure() == \
                'User Group / Instrument / Full Name / Dataset':
            if self.IgnoreOldDatasets():
                datasetCount = 0
                for folder in dirsDepth4:
                    ctimestamp = os.path.getctime(folder)
                    ctime = datetime.fromtimestamp(ctimestamp)
                    age = datetime.now() - ctime
                    if age.total_seconds() <= ignoreIntervalSeconds:
                        datasetCount += 1
            else:
                datasetCount = len(dirsDepth4)

        logger.debug("SettingsModel folder structure validation succeeded!")
        self.validation = SettingsValidation(True, datasetCount=datasetCount)
        return self.validation
        # End PerformFolderStructureValidation

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
        facilities = FacilityModel.GetMyFacilities(self)
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

    def GetLastSettingsUpdateTrigger(self):
        return self.last_settings_update_trigger

    def SetLastSettingsUpdateTrigger(self, lastSettingsUpdateTrigger):
        self.last_settings_update_trigger = lastSettingsUpdateTrigger

    def GetConnectivityCheckInterval(self):
        return self.connectivityCheckInterval

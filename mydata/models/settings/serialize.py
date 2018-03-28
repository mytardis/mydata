"""
Methods for saving / loading / retrieving settings between the
global SETTINGS singleton, the settings dialog, and the MyData.cfg file.

The global SETTINGS singleton is imported inline when needed to avoid
circular dependencies.

The methods for loading settings from disk and checking for updates
on the MyTardis server can't use the global SETTINGS singleton, because
they are called from SettingsModel's constructor which would cause a
circular dependency, so we pass the settings as an argument instead.
"""
import traceback
import os
import sys
# For Python 3, this will change to "from configparser import ConfigParser":
from ConfigParser import ConfigParser
from datetime import datetime

import appdirs
import requests

from ...logs import logger
from .miscellaneous import LastSettingsUpdateTrigger

OLD_DEFAULT_CONFIG_PATH = os.path.join(
    appdirs.user_data_dir("MyData", "Monash University"), "MyData.cfg")
if sys.platform.startswith("win"):
    NEW_DEFAULT_CONFIG_PATH = os.path.join(
        appdirs.site_config_dir("MyData", "Monash University"), "MyData.cfg")
else:
    NEW_DEFAULT_CONFIG_PATH = OLD_DEFAULT_CONFIG_PATH


def LoadSettings(settings, configPath=None, checkForUpdates=True):
    """
    :param settings: Object of class SettingsModel to load the settings into.
    :param configPath: Path to MyData.cfg
    :param checkForUpdates: Whether to look for updated settings in the
                            UploaderSettings model on the MyTardis server.

    Sets some default values for settings fields, then loads a settings file,
    e.g. C:\\ProgramData\\Monash University\\MyData\\MyData.cfg
    or /Users/jsmith/Library/Application Support/MyData/MyData.cfg
    """
    settings.SetDefaultConfig()

    if configPath is None:
        configPath = settings.configPath

    if sys.platform.startswith("win") and \
            configPath == NEW_DEFAULT_CONFIG_PATH and \
            not os.path.exists(configPath):
        if os.path.exists(OLD_DEFAULT_CONFIG_PATH):
            configPath = OLD_DEFAULT_CONFIG_PATH

    if configPath is not None and os.path.exists(configPath):
        logger.info("Reading settings from: " + configPath)
        try:
            configParser = ConfigParser()
            configParser.read(configPath)
            LoadGeneralSettings(settings, configParser)
            LoadScheduleSettings(settings, configParser)
            LoadFilterSettings(settings, configParser)
            LoadAdvancedSettings(settings, configParser)
            LoadMiscellaneousSettings(settings, configParser)
        except:
            logger.error(traceback.format_exc())

    if settings.miscellaneous.uuid and checkForUpdates:
        if CheckForUpdatedSettingsOnServer(settings):
            logger.debug("Updated local settings from server.")
        else:
            logger.debug("Settings were not updated from the server.")

    settings.lastSettingsUpdateTrigger = \
        LastSettingsUpdateTrigger.READ_FROM_DISK


def LoadGeneralSettings(settings, configParser):
    """
    :param settings: Object of class SettingsModel to load the settings into.
    :param configParser: The ConfigParser object which stores data read from
                         MyData.cfg

    Loads General settings from a ConfigParser object.

    These settings appear in the General tab of the settings dialog.
    """
    configFileSection = "MyData"
    fields = ["instrument_name", "facility_name", "data_directory",
              "contact_name", "contact_email", "mytardis_url",
              "username", "api_key"]
    for field in fields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.get(configFileSection, field)


def LoadScheduleSettings(settings, configParser):
    """
    :param settings: Object of class SettingsModel to load the settings into.
    :param configParser: The ConfigParser object which stores data read from
                         MyData.cfg

    Loads Schedule settings from a ConfigParser object

    These settings appear in the Schedule tab of the settings dialog.
    """
    configFileSection = "MyData"
    fields = ["schedule_type", "monday_checked", "tuesday_checked",
              "wednesday_checked", "thursday_checked",
              "friday_checked", "saturday_checked", "sunday_checked",
              "scheduled_date", "scheduled_time",
              "timer_minutes", "timer_from_time", "timer_to_time"]
    for field in fields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.get(configFileSection, field)
    intFields = ["ignore_interval_number", "ignore_new_files_minutes"]
    for field in intFields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.getint(configFileSection, field)
    if configParser.has_option(configFileSection, "scheduled_date"):
        datestring = configParser.get(configFileSection, "scheduled_date")
        settings['scheduled_date'] = \
            datetime.date(datetime.strptime(datestring, "%Y-%m-%d"))
    if configParser.has_option(configFileSection, "scheduled_time"):
        timestring = configParser.get(configFileSection, "scheduled_time")
        settings['scheduled_time'] = datetime.strptime(timestring, "%H:%M:%S")
        settings['scheduled_time'] = datetime.time(settings['scheduled_time'])
    if configParser.has_option(configFileSection, "timer_minutes"):
        settings['timer_minutes'] = \
            configParser.getint(configFileSection, "timer_minutes")
    if configParser.has_option(configFileSection, "timer_from_time"):
        timestring = configParser.get(configFileSection, "timer_from_time")
        settings['timer_from_time'] = datetime.strptime(timestring, "%H:%M:%S")
        settings['timer_from_time'] = \
            datetime.time(settings['timer_from_time'])
    if configParser.has_option(configFileSection, "timer_to_time"):
        timestring = configParser.get(configFileSection, "timer_to_time")
        settings['timer_to_time'] = datetime.strptime(timestring, "%H:%M:%S")
        settings['timer_to_time'] = datetime.time(settings['timer_to_time'])
    for day in ["monday_checked", "tuesday_checked", "wednesday_checked",
                "thursday_checked", "friday_checked", "saturday_checked",
                "sunday_checked"]:
        if configParser.has_option(configFileSection, day):
            settings[day] = configParser.getboolean(configFileSection, day)


def LoadFilterSettings(settings, configParser):
    """
    :param settings: Object of class SettingsModel to load the settings into.
    :param configParser: The ConfigParser object which stores data read from
                         MyData.cfg

    Loads Filter settings from a ConfigParser object

    These settings appear in the Filter tab of the settings dialog.
    """
    configFileSection = "MyData"
    fields = [
        "user_filter", "dataset_filter", "experiment_filter",
        "includes_file", "excludes_file",
        "ignore_interval_unit", "ignore_new_interval_unit"
    ]
    for field in fields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.get(configFileSection, field)
    booleanFields = [
        "ignore_old_datasets", "ignore_new_datasets", "ignore_new_files",
        "use_includes_file", "use_excludes_file"
    ]
    for field in booleanFields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.getboolean(configFileSection, field)
    intFields = [
        "ignore_interval_number", "ignore_new_interval_number",
        "ignore_new_files_minutes"
    ]
    for field in intFields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.getint(configFileSection, field)


def LoadAdvancedSettings(settings, configParser):
    """
    :param settings: Object of class SettingsModel to load the settings into.
    :param configParser: The ConfigParser object which stores data read from
                         MyData.cfg

    Loads Advanced settings from a ConfigParser object

    These settings appear in the Advanced tab of the settings dialog.
    """
    configFileSection = "MyData"
    fields = ["folder_structure", "dataset_grouping", "group_prefix",
              "max_upload_threads", "max_upload_retries",
              "validate_folder_structure", "start_automatically_on_login",
              "upload_invalid_user_folders"]
    for field in fields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.get(configFileSection, field)
    booleanFields = ["validate_folder_structure",
                     "start_automatically_on_login",
                     "upload_invalid_user_folders"]
    for field in booleanFields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.getboolean(configFileSection, field)
    intFields = ["max_upload_threads", "max_upload_retries"]
    for field in intFields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.getint(configFileSection, field)


def LoadMiscellaneousSettings(settings, configParser):
    """
    :param settings: Object of class SettingsModel to load the settings into.
    :param configParser: The ConfigParser object which stores data read from
                         MyData.cfg

    Loads Miscellaneous settings from a ConfigParser object

    These settings don't appear in the settings dialog, except for "locked",
    which is visible in the settings dialog, but not within any one tab view.
    """
    configFileSection = "MyData"
    fields = ["locked", "uuid", "cipher", "use_none_cipher",
              "max_verification_threads", "verification_delay",
              "fake_md5_sum", "progress_poll_interval", "immutable_datasets",
              "cache_datafile_lookups", "connection_timeout"]
    for field in fields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.get(configFileSection, field)
    booleanFields = [
        "fake_md5_sum", "use_none_cipher", "locked", "immutable_datasets",
        "cache_datafile_lookups"]
    for field in booleanFields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.getboolean(configFileSection, field)
    intFields = ["max_verification_threads"]
    for field in intFields:
        if configParser.has_option(configFileSection, field):
            settings[field] = configParser.getint(configFileSection, field)
    floatFields = [
        "verification_delay", "progress_poll_interval", "connection_timeout"]
    for field in floatFields:
        if configParser.has_option(configFileSection, field):
            try:
                settings[field] = configParser.getfloat(configFileSection, field)
            except ValueError:
                logger.warning("Couldn't read value for %s, using default instead." % field)
                settings[field] = settings.miscellaneous.default[field]


def CheckForUpdatedSettingsOnServer(settings):
    """
    Check for updated settings on server.
    """
    uploaderModel = settings.uploaderModel
    try:
        localModTime = \
            datetime.fromtimestamp(os.stat(settings.configPath).st_mtime)
    except OSError:
        localModTime = datetime.fromtimestamp(0)
    try:
        settingsFromServer = uploaderModel.GetSettings()
        settingsUpdated = uploaderModel.settingsUpdated
    except requests.exceptions.RequestException as err:
        logger.error(err)
        settingsFromServer = None
        settingsUpdated = datetime.fromtimestamp(0)
    if settingsFromServer and settingsUpdated and \
            settingsUpdated > localModTime:
        logger.debug("Settings will be updated from the server.")
        for setting in settingsFromServer:
            try:
                settings[setting['key']] = setting['value']
                if setting['key'] in (
                        "ignore_old_datasets", "ignore_new_datasets",
                        "ignore_new_files",
                        "validate_folder_structure",
                        "start_automatically_on_login",
                        "upload_invalid_user_folders",
                        "fake_md5_sum", "use_none_cipher", "locked",
                        "monday_checked", "tuesday_checked",
                        "wednesday_checked", "thursday_checked",
                        "friday_checked", "saturday_checked",
                        "sunday_checked", "use_includes_file",
                        "use_excludes_file", "immutable_datasets",
                        "cache_datafile_lookups"):
                    settings[setting['key']] = (setting['value'] == "True")
                if setting['key'] in (
                        "timer_minutes", "ignore_interval_number",
                        "ignore_new_files_minutes",
                        "max_verification_threads",
                        "max_upload_threads", "max_upload_retries"):
                    settings[setting['key']] = int(setting['value'])
                elif setting['key'] in (
                        "progress_poll_interval", "verification_delay",
                        "connection_timeout"):
                    try:
                        settings[setting['key']] = float(setting['value'])
                    except ValueError:
                        field = setting['key']
                        logger.warning("Couldn't read value for %s, using default instead." % field)
                        settings[field] = settings.miscellaneous.default[field]
                if setting['key'] in (
                        "scheduled_date"):
                    settings[setting['key']] = \
                        datetime.date(datetime.strptime(setting['value'],
                                                        "%Y-%m-%d"))
                if setting['key'] in (
                        "scheduled_time", "timer_from_time",
                        "timer_to_time"):
                    settings[setting['key']] = \
                        datetime.time(datetime.strptime(setting['value'],
                                                        "%H:%M:%S"))
            except KeyError as err:
                logger.warning(
                    "Settings field '%s' found on server is not understood "
                    "by this version of MyData." % setting['key'])
        return True
    return False


def SaveSettingsToDisk(configPath=None):
    """
    Save configuration to disk.
    """
    from ...settings import SETTINGS
    if configPath is None:
        configPath = SETTINGS.configPath
    if configPath is None:
        raise Exception("SaveSettingsToDisk called "
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
                  "includes_file", "excludes_file",
                  "folder_structure",
                  "dataset_grouping", "group_prefix",
                  "ignore_old_datasets", "ignore_interval_number",
                  "ignore_interval_unit", "ignore_new_datasets",
                  "ignore_new_interval_number", "ignore_new_interval_unit",
                  "ignore_new_files", "ignore_new_files_minutes",
                  "use_includes_file", "use_excludes_file",
                  "max_verification_threads",
                  "max_upload_threads", "max_upload_retries",
                  "validate_folder_structure", "fake_md5_sum",
                  "cipher", "locked", "uuid", "use_none_cipher",
                  "progress_poll_interval", "verification_delay",
                  "start_automatically_on_login", "immutable_datasets",
                  "cache_datafile_lookups", "upload_invalid_user_folders",
                  "connection_timeout"]
        settingsList = []
        for field in fields:
            value = SETTINGS[field]
            configParser.set("MyData", field, value)
            settingsList.append(dict(key=field, value=str(value)))
        configParser.write(configFile)
    logger.info("Saved settings to " + configPath)
    if SETTINGS.uploaderModel:
        try:
            SETTINGS.uploaderModel.UpdateSettings(settingsList)
        except requests.exceptions.RequestException as err:
            logger.error(err)


def SaveFieldsFromDialog(settingsDialog, configPath=None, saveToDisk=True):
    """
    Save fields from settings dialog to the global SETTINGS singleton.

    When the Settings dialog's OK button is clicked, we call this with
    saveToDisk=False, to save the dialog's settings to a temporary
    settings model instance which we can validate.  Then if the settings
    are valid, we call this again with saveToDisk=True.
    """
    from ...settings import SETTINGS
    SETTINGS.SavePrevious()

    if configPath is None:
        configPath = SETTINGS.configPath

    # General tab
    SETTINGS.general.instrumentName = settingsDialog.GetInstrumentName()
    SETTINGS.general.facilityName = settingsDialog.GetFacilityName()
    SETTINGS.general.myTardisUrl = settingsDialog.GetMyTardisUrl()
    SETTINGS.general.contactName = settingsDialog.GetContactName()
    SETTINGS.general.contactEmail = settingsDialog.GetContactEmail()
    SETTINGS.general.dataDirectory = settingsDialog.GetDataDirectory()
    SETTINGS.general.username = settingsDialog.GetUsername()
    SETTINGS.general.apiKey = settingsDialog.GetApiKey()

    # Schedule tab
    SETTINGS.schedule.scheduleType = settingsDialog.GetScheduleType()
    SETTINGS.schedule.mondayChecked = settingsDialog.IsMondayChecked()
    SETTINGS.schedule.tuesdayChecked = settingsDialog.IsTuesdayChecked()
    SETTINGS.schedule.wednesdayChecked = settingsDialog.IsWednesdayChecked()
    SETTINGS.schedule.thursdayChecked = settingsDialog.IsThursdayChecked()
    SETTINGS.schedule.fridayChecked = settingsDialog.IsFridayChecked()
    SETTINGS.schedule.saturdayChecked = settingsDialog.IsSaturdayChecked()
    SETTINGS.schedule.sundayChecked = settingsDialog.IsSundayChecked()
    SETTINGS.schedule.scheduledDate = settingsDialog.GetScheduledDate()
    SETTINGS.schedule.scheduledTime = settingsDialog.GetScheduledTime()
    SETTINGS.schedule.timerMinutes = settingsDialog.GetTimerMinutes()
    SETTINGS.schedule.timerFromTime = settingsDialog.GetTimerFromTime()
    SETTINGS.schedule.timerToTime = settingsDialog.GetTimerToTime()

    # Filters tab
    SETTINGS.filters.userFilter = settingsDialog.GetUserFilter()
    SETTINGS.filters.datasetFilter = settingsDialog.GetDatasetFilter()
    SETTINGS.filters.experimentFilter = settingsDialog.GetExperimentFilter()
    SETTINGS.filters.ignoreOldDatasets = settingsDialog.IgnoreOldDatasets()
    SETTINGS.filters.ignoreOldDatasetIntervalNumber = \
        settingsDialog.GetIgnoreOldDatasetIntervalNumber()
    SETTINGS.filters.ignoreOldDatasetIntervalUnit = \
        settingsDialog.GetIgnoreOldDatasetIntervalUnit()
    SETTINGS.filters.ignoreNewFiles = settingsDialog.IgnoreNewFiles()
    SETTINGS.filters.ignoreNewFilesMinutes = \
        settingsDialog.GetIgnoreNewFilesMinutes()
    SETTINGS.filters.useIncludesFile = settingsDialog.UseIncludesFile()
    SETTINGS.filters.includesFile = settingsDialog.GetIncludesFile()
    SETTINGS.filters.useExcludesFile = settingsDialog.UseExcludesFile()
    SETTINGS.filters.excludesFile = settingsDialog.GetExcludesFile()

    # Advanced tab
    SETTINGS.advanced.folderStructure = settingsDialog.GetFolderStructure()
    SETTINGS.advanced.datasetGrouping = settingsDialog.GetDatasetGrouping()
    SETTINGS.advanced.groupPrefix = settingsDialog.GetGroupPrefix()
    SETTINGS.advanced.validateFolderStructure = \
        settingsDialog.ValidateFolderStructure()
    SETTINGS.advanced.startAutomaticallyOnLogin = \
        settingsDialog.StartAutomaticallyOnLogin()
    SETTINGS.advanced.uploadInvalidUserOrGroupFolders = \
        settingsDialog.UploadInvalidUserOrGroupFolders()
    SETTINGS.advanced.maxUploadThreads = settingsDialog.GetMaxUploadThreads()
    SETTINGS.advanced.maxUploadRetries = settingsDialog.GetMaxUploadRetries()

    SETTINGS.miscellaneous.locked = settingsDialog.Locked()

    if saveToDisk:
        SaveSettingsToDisk(configPath)

    SETTINGS.lastSettingsUpdateTrigger = LastSettingsUpdateTrigger.UI_RESPONSE

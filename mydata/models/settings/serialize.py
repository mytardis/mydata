"""
Model classes for the settings displayed in the settings dialog
and saved to disk in MyData.cfg
"""
import traceback
import os
from ConfigParser import ConfigParser
from datetime import datetime

import requests

from mydata.logs import logger
from .miscellaneous import LastSettingsUpdateTrigger


def LoadSettings(settingsModel, configPath=None, checkForUpdates=True):
    """
    Sets some default values for settings fields, then loads a settings
    file,
    e.g. C:\\Users\\jsmith\\AppData\\Local\\Monash University\\MyData\\MyData.cfg
    """
    settingsModel.SetDefaultConfig()

    if configPath is None:
        configPath = settingsModel.configPath

    if configPath is not None and os.path.exists(configPath):
        logger.info("Reading settings from: " + configPath)
        try:
            configParser = ConfigParser()
            configParser.read(configPath)
            LoadGeneralSettings(settingsModel, configParser)
            LoadScheduleSettings(settingsModel, configParser)
            LoadFilterSettings(settingsModel, configParser)
            LoadAdvancedSettings(settingsModel, configParser)
            LoadMiscellaneousSettings(settingsModel, configParser)
        except:
            logger.error(traceback.format_exc())

    if settingsModel.miscellaneous.uuid and checkForUpdates:
        if CheckForUpdatedSettingsOnServer(settingsModel):
            logger.debug("Updated local settings from server.")
        else:
            logger.debug("Settings were not updated from the server.")

    settingsModel.previousDict.update(settingsModel.__dict__)

    settingsModel.lastSettingsUpdateTrigger = \
        LastSettingsUpdateTrigger.READ_FROM_DISK


def LoadGeneralSettings(settingsModel, configParser):
    """
    Loads General settings from a ConfigParser object.

    These settings appear in the General tab of the settings dialog.
    """
    configFileSection = "MyData"
    fields = ["instrument_name", "facility_name", "data_directory",
              "contact_name", "contact_email", "mytardis_url",
              "username", "api_key"]
    for field in fields:
        if configParser.has_option(configFileSection, field):
            settingsModel[field] = \
                configParser.get(configFileSection, field)


def LoadScheduleSettings(settingsModel, configParser):
    """
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
            settingsModel[field] = \
                configParser.get(configFileSection, field)
    intFields = ["ignore_interval_number", "ignore_new_files_minutes"]
    for field in intFields:
        if configParser.has_option(configFileSection, field):
            settingsModel[field] = \
                configParser.getint(configFileSection, field)
    if configParser.has_option(configFileSection, "scheduled_date"):
        datestring = configParser.get(configFileSection, "scheduled_date")
        settingsModel['scheduled_date'] = \
            datetime.date(datetime.strptime(datestring, "%Y-%m-%d"))
    if configParser.has_option(configFileSection, "scheduled_time"):
        timestring = configParser.get(configFileSection, "scheduled_time")
        settingsModel['scheduled_time'] = \
            datetime.strptime(timestring, "%H:%M:%S")
        settingsModel['scheduled_time'] = \
            datetime.time(settingsModel['scheduled_time'])
    if configParser.has_option(configFileSection, "timer_minutes"):
        settingsModel['timer_minutes'] = \
            configParser.getint(configFileSection, "timer_minutes")
    if configParser.has_option(configFileSection, "timer_from_time"):
        timestring = configParser.get(configFileSection, "timer_from_time")
        settingsModel['timer_from_time'] = \
            datetime.strptime(timestring, "%H:%M:%S")
        settingsModel['timer_from_time'] = \
            datetime.time(settingsModel['timer_from_time'])
    if configParser.has_option(configFileSection, "timer_to_time"):
        timestring = configParser.get(configFileSection, "timer_to_time")
        settingsModel['timer_to_time'] = \
            datetime.strptime(timestring, "%H:%M:%S")
        settingsModel['timer_to_time'] = \
            datetime.time(settingsModel['timer_to_time'])
    for day in ["monday_checked", "tuesday_checked", "wednesday_checked",
                "thursday_checked", "friday_checked", "saturday_checked",
                "sunday_checked"]:
        if configParser.has_option(configFileSection, day):
            settingsModel[day] = \
                configParser.getboolean(configFileSection, day)


def LoadFilterSettings(settingsModel, configParser):
    """
    Loads Filter settings from a ConfigParser object

    These settings appear in the Filter tab of the settings dialog.
    """
    configFileSection = "MyData"
    fields = ["user_filter", "dataset_filter", "experiment_filter",
              "includes_file", "excludes_file", "ignore_interval_unit"]
    for field in fields:
        if configParser.has_option(configFileSection, field):
            settingsModel[field] = \
                configParser.get(configFileSection, field)
    booleanFields = ["ignore_old_datasets", "ignore_new_files",
                     "use_includes_file", "use_excludes_file"]
    for field in booleanFields:
        if configParser.has_option(configFileSection, field):
            settingsModel[field] = \
                configParser.getboolean(configFileSection, field)
    intFields = ["ignore_interval_number", "ignore_new_files_minutes"]
    for field in intFields:
        if configParser.has_option(configFileSection, field):
            settingsModel[field] = \
                configParser.getint(configFileSection, field)


def LoadAdvancedSettings(settingsModel, configParser):
    """
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
            settingsModel[field] = \
                configParser.get(configFileSection, field)
    booleanFields = ["validate_folder_structure",
                     "start_automatically_on_login",
                     "upload_invalid_user_folders"]
    for field in booleanFields:
        if configParser.has_option(configFileSection, field):
            settingsModel[field] = \
                configParser.getboolean(configFileSection, field)
    intFields = ["max_upload_threads", "max_upload_retries"]
    for field in intFields:
        if configParser.has_option(configFileSection, field):
            settingsModel[field] = \
                configParser.getint(configFileSection, field)


def LoadMiscellaneousSettings(settingsModel, configParser):
    """
    Loads Miscellaneous settings from a ConfigParser object

    These settings don't appear in the settings dialog, except for "locked",
    which is visible in the settings dialog, but not within any one tab view.

    verification_delay and progress_poll_interval are stored as strings,
    but then coverted to floats in:
    mydata.models.settings.miscellaneous.MiscellaneousSettingsModel's
    "verificationDelay" and "progressPollInterval" properties.
    """
    configFileSection = "MyData"
    fields = ["locked", "uuid", "cipher", "use_none_cipher",
              "max_verification_threads", "verification_delay",
              "fake_md5_sum", "progress_poll_interval"]
    for field in fields:
        if configParser.has_option(configFileSection, field):
            settingsModel[field] = \
                configParser.get(configFileSection, field)
    booleanFields = ["fake_md5_sum", "use_none_cipher", "locked"]
    for field in booleanFields:
        if configParser.has_option(configFileSection, field):
            settingsModel[field] = \
                configParser.getboolean(configFileSection, field)
    intFields = ["max_verification_threads"]
    for field in intFields:
        if configParser.has_option(configFileSection, field):
            settingsModel[field] = \
                configParser.getint(configFileSection, field)


def CheckForUpdatedSettingsOnServer(settingsModel):
    """
    Check for updated settings on server.
    """
    uploaderModel = settingsModel.uploaderModel
    try:
        localModTime = \
            datetime.fromtimestamp(os.stat(settingsModel.configPath).st_mtime)
    except OSError:
        localModTime = datetime.fromtimestamp(0)
    try:
        settingsFromServer = uploaderModel.GetSettings()
        settingsUpdated = uploaderModel.GetSettingsUpdated()
    except requests.exceptions.RequestException as err:
        logger.error(err)
        settingsFromServer = None
        settingsUpdated = datetime.fromtimestamp(0)
    if settingsFromServer and settingsUpdated and \
            settingsUpdated > localModTime:
        logger.debug("Settings will be updated from the server.")
        for setting in settingsFromServer:
            settingsModel[setting['key']] = setting['value']
            if setting['key'] in (
                    "ignore_old_datasets", "ignore_new_files",
                    "validate_folder_structure",
                    "start_automatically_on_login",
                    "upload_invalid_user_folders",
                    "fake_md5_sum", "use_none_cipher", "locked",
                    "monday_checked", "tuesday_checked",
                    "wednesday_checked", "thursday_checked",
                    "friday_checked", "saturday_checked",
                    "sunday_checked", "use_includes_file",
                    "use_excludes_file"):
                settingsModel[setting['key']] = \
                    (setting['value'] == "True")
            if setting['key'] in (
                    "timer_minutes", "ignore_interval_number",
                    "ignore_new_files_minutes",
                    "progress_poll_interval", "verification_delay",
                    "max_verification_threads",
                    "max_upload_threads", "max_upload_retries"):
                settingsModel[setting['key']] = int(setting['value'])
            if setting['key'] in (
                    "scheduled_date"):
                settingsModel[setting['key']] = \
                    datetime.date(datetime.strptime(setting['value'],
                                                    "%Y-%m-%d"))
            if setting['key'] in (
                    "scheduled_time", "timer_from_time",
                    "timer_to_time"):
                settingsModel[setting['key']] = \
                    datetime.time(datetime.strptime(setting['value'],
                                                    "%H:%M:%S"))
        return True
    return False


def SaveSettingsToDisk(settingsModel, configPath=None):
    """
    Save configuration to disk.
    """
    if configPath is None:
        configPath = settingsModel.configPath
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
                  "ignore_interval_unit",
                  "ignore_new_files", "ignore_new_files_minutes",
                  "use_includes_file", "use_excludes_file",
                  "max_verification_threads",
                  "max_upload_threads", "max_upload_retries",
                  "validate_folder_structure", "fake_md5_sum",
                  "cipher", "locked", "uuid", "use_none_cipher",
                  "progress_poll_interval", "verification_delay",
                  "start_automatically_on_login",
                  "upload_invalid_user_folders"]
        settingsList = []
        for field in fields:
            value = settingsModel[field]
            configParser.set("MyData", field, value)
            settingsList.append(dict(key=field, value=str(value)))
        configParser.write(configFile)
    logger.info("Saved settings to " + configPath)
    if settingsModel.uploaderModel:
        try:
            settingsModel.uploaderModel.UpdateSettings(settingsList)
        except requests.exceptions.RequestException as err:
            logger.error(err)


def SaveFieldsFromDialog(settingsModel, settingsDialog, configPath=None,
                         saveToDisk=True):
    """
    Save fields from settings dialog to setings model
    """
    settingsModel.previousDict.update(settingsModel.__dict__)
    if configPath is None:
        configPath = settingsModel.configPath

    # General tab
    settingsModel.general.instrumentName = settingsDialog.GetInstrumentName()
    settingsModel.general.facilityName = settingsDialog.GetFacilityName()
    settingsModel.general.myTardisUrl = settingsDialog.GetMyTardisUrl()
    settingsModel.general.contactName = settingsDialog.GetContactName()
    settingsModel.general.contactEmail = settingsDialog.GetContactEmail()
    settingsModel.general.dataDirectory = settingsDialog.GetDataDirectory()
    settingsModel.general.username = settingsDialog.GetUsername()
    settingsModel.general.apiKey = settingsDialog.GetApiKey()

    # Schedule tab
    settingsModel.schedule.scheduleType = settingsDialog.GetScheduleType()
    settingsModel.schedule.mondayChecked = settingsDialog.IsMondayChecked()
    settingsModel.schedule.tuesdayChecked = settingsDialog.IsTuesdayChecked()
    settingsModel.schedule.wednesdayChecked = settingsDialog.IsWednesdayChecked()
    settingsModel.schedule.thursdayChecked = settingsDialog.IsThursdayChecked()
    settingsModel.schedule.fridayChecked = settingsDialog.IsFridayChecked()
    settingsModel.schedule.saturdayChecked = settingsDialog.IsSaturdayChecked()
    settingsModel.schedule.sundayChecked = settingsDialog.IsSundayChecked()
    settingsModel.schedule.scheduledDate = settingsDialog.GetScheduledDate()
    settingsModel.schedule.scheduledTime = settingsDialog.GetScheduledTime()
    settingsModel.schedule.timerMinutes = settingsDialog.GetTimerMinutes()
    settingsModel.schedule.timerFromTime = settingsDialog.GetTimerFromTime()
    settingsModel.schedule.timerToTime = settingsDialog.GetTimerToTime()

    # Filters tab
    settingsModel.filters.userFilter = settingsDialog.GetUserFilter()
    settingsModel.filters.datasetFilter = settingsDialog.GetDatasetFilter()
    settingsModel.filters.experimentFilter = settingsDialog.GetExperimentFilter()
    settingsModel.filters.ignoreOldDatasets = settingsDialog.IgnoreOldDatasets()
    settingsModel.filters.ignoreOldDatasetIntervalNumber = \
        settingsDialog.GetIgnoreOldDatasetIntervalNumber()
    settingsModel.filters.ignoreOldDatasetIntervalUnit = \
        settingsDialog.GetIgnoreOldDatasetIntervalUnit()
    settingsModel.filters.ignoreNewFiles = settingsDialog.IgnoreNewFiles()
    settingsModel.filters.ignoreNewFilesMinutes = \
        settingsDialog.GetIgnoreNewFilesMinutes()
    settingsModel.filters.useIncludesFile = settingsDialog.UseIncludesFile()
    settingsModel.filters.includesFile = settingsDialog.GetIncludesFile()
    settingsModel.filters.useExcludesFile = settingsDialog.UseExcludesFile()
    settingsModel.filters.excludesFile = settingsDialog.GetExcludesFile()

    # Advanced tab
    settingsModel.advanced.folderStructure = settingsDialog.GetFolderStructure()
    settingsModel.advanced.datasetGrouping = settingsDialog.GetDatasetGrouping()
    settingsModel.advanced.groupPrefix = settingsDialog.GetGroupPrefix()
    settingsModel.advanced.validateFolderStructure = \
        settingsDialog.ValidateFolderStructure()
    settingsModel.advanced.startAutomaticallyOnLogin = \
        settingsDialog.StartAutomaticallyOnLogin()
    settingsModel.advanced.uploadInvalidUserOrGroupFolders = \
        settingsDialog.UploadInvalidUserOrGroupFolders()
    settingsModel.advanced.maxUploadThreads = settingsDialog.GetMaxUploadThreads()
    settingsModel.advanced.maxUploadRetries = settingsDialog.GetMaxUploadRetries()

    settingsModel.miscellaneous.locked = settingsDialog.Locked()

    if saveToDisk:
        SaveSettingsToDisk(settingsModel, configPath)

    settingsModel.lastSettingsUpdateTrigger = \
        LastSettingsUpdateTrigger.UI_RESPONSE

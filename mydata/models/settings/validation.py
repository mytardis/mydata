"""
Methods for validating settings.

The global SETTINGS singleton is imported inline to avoid
circular dependencies.
"""
import traceback
import os
import sys
from glob import glob
from datetime import datetime

import requests
from validate_email import validate_email
import wx

from ...logs import logger
from ...utils.autostart import UpdateAutostartFile
from ...utils.exceptions import InvalidSettings
from ...utils.exceptions import Unauthorized
from ...utils.exceptions import UserAbortedSettingsValidation
from ..facility import FacilityModel
from .miscellaneous import LastSettingsUpdateTrigger

DEFAULT_TIMEOUT = 5


def ValidateSettings(setStatusMessage=None, testRun=False):
    """
    Validate SETTINGS (an instance of SettingsModel)
    """
    from ...settings import SETTINGS

    datasetCount = -1

    def LogIfTestRun(message):
        """
        Log message if this is a Test Run
        """
        if testRun:
            logger.testrun(message)

    try:
        CheckIfShouldAbort(setStatusMessage)
        CheckForMissingRequiredField()
        LogIfTestRun("Folder structure: %s"
                     % SETTINGS.advanced.folderStructure)
        WarnIfIgnoringInvalidUserFolders(testRun)
        CheckFilters(setStatusMessage, testRun)
        CheckIfShouldAbort(setStatusMessage)
        if SETTINGS.advanced.validateFolderStructure:
            datasetCount = CheckStructureAndCountDatasets(setStatusMessage)
        CheckIfShouldAbort(setStatusMessage)
        CheckMyTardisUrl(setStatusMessage, testRun)
        CheckIfShouldAbort(setStatusMessage)
        CheckMyTardisCredentials(setStatusMessage)
        CheckIfShouldAbort(setStatusMessage)
        CheckFacility(setStatusMessage)
        CheckIfShouldAbort(setStatusMessage)
        CheckInstrument(setStatusMessage)
        CheckIfShouldAbort(setStatusMessage)
        CheckContactEmailAndEmailFolders(setStatusMessage)
        CheckIfShouldAbort(setStatusMessage)
        if SETTINGS.lastSettingsUpdateTrigger == \
                LastSettingsUpdateTrigger.UI_RESPONSE \
                and not sys.platform.startswith("win"):
            CheckAutostart(setStatusMessage)
        CheckIfShouldAbort(setStatusMessage)
        CheckScheduledTime()
        message = "Settings validation - succeeded!"
        logger.debug(message)
        LogIfTestRun(message)
        if setStatusMessage:
            setStatusMessage(message)
        return datasetCount
    except Exception as err:
        if isinstance(err, InvalidSettings):
            raise
        if isinstance(err, UserAbortedSettingsValidation):
            raise
        logger.error(traceback.format_exc())
        message = str(err)
        LogIfTestRun("ERROR: %s" % message)
        raise InvalidSettings(message, "")


def CheckForMissingRequiredField():
    """
    Check if a required field is missing
    """
    from ...settings import SETTINGS
    if SETTINGS.general.instrumentName.strip() == "":
        message = "Please enter a valid instrument name."
        raise InvalidSettings(message, "instrument_name")
    if SETTINGS.general.dataDirectory.strip() == "":
        message = "Please enter a valid data directory."
        raise InvalidSettings(message, "data_directory")
    if SETTINGS.general.myTardisUrl.strip() == "":
        message = "Please enter a valid MyTardis URL, " \
            "beginning with \"http://\" or \"https://\"."
        raise InvalidSettings(message, "mytardis_url")
    if SETTINGS.general.contactName.strip() == "":
        message = "Please enter a valid contact name."
        raise InvalidSettings(message, "contact_name")
    if SETTINGS.general.contactEmail.strip() == "":
        message = "Please enter a valid contact email."
        raise InvalidSettings(message, "contact_email")
    if SETTINGS.general.username.strip() == "":
        message = "Please enter a MyTardis username."
        raise InvalidSettings(message, "username")
    if SETTINGS.general.apiKey.strip() == "":
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
            % SETTINGS.general.username.strip()
        raise InvalidSettings(message, "api_key")
    if not os.path.exists(SETTINGS.general.dataDirectory):
        message = "The data directory: \"%s\" doesn't exist!" % \
            SETTINGS.general.dataDirectory
        raise InvalidSettings(message, "data_directory")


def WarnIfIgnoringInvalidUserFolders(testRun):
    """
    Warn if ignoring invalid user (or group) folders
    """
    from ...settings import SETTINGS

    def LogIfTestRun(message):
        """
        Log message if this is a Test Run
        """
        if testRun:
            logger.testrun(message)

    if not SETTINGS.advanced.uploadInvalidUserOrGroupFolders:
        if SETTINGS.advanced.folderStructure.startswith("User Group"):
            message = "Invalid user group folders are being ignored."
            logger.warning(message)
            LogIfTestRun("WARNING: %s" % message)
        elif "User" in SETTINGS.advanced.folderStructure or \
                "Email" in SETTINGS.advanced.folderStructure:
            message = "Invalid user folders are being ignored."
            logger.warning(message)
            LogIfTestRun("WARNING: %s" % message)


def CheckFilters(setStatusMessage, testRun):
    """
    Check filter-related fields
    """
    from ...settings import SETTINGS

    def LogIfTestRun(message):
        """
        Log message if this is a Test Run
        """
        if testRun:
            logger.testrun(message)

    if SETTINGS.filters.userFilter.strip() != "":
        if SETTINGS.advanced.folderStructure.startswith("User Group"):
            message = "User group folders are being filtered."
            logger.warning(message)
            LogIfTestRun("WARNING: %s" % message)
        else:
            message = "User folders are being filtered."
            logger.warning(message)
            LogIfTestRun("WARNING: %s" % message)
    if SETTINGS.filters.datasetFilter.strip() != "":
        message = "Dataset folders are being filtered."
        logger.warning(message)
        LogIfTestRun("WARNING: %s" % message)
    if SETTINGS.filters.experimentFilter.strip() != "":
        message = "Experiment folders are being filtered."
        logger.warning(message)
        LogIfTestRun("WARNING: %s" % message)
    if SETTINGS.filters.ignoreOldDatasets:
        message = "Old datasets are being ignored."
        logger.warning(message)
        LogIfTestRun("WARNING: %s" % message)
    if SETTINGS.filters.ignoreNewFiles:
        message = "Files newer than %s minute(s) are being ignored." \
            % SETTINGS.filters.ignoreNewFilesMinutes
        logger.warning(message)
        LogIfTestRun("WARNING: %s" % message)
    if SETTINGS.filters.useIncludesFile \
            and not SETTINGS.filters.useExcludesFile:
        message = "Only files matching patterns in includes " \
            "file will be scanned for upload."
        logger.warning(message)
        LogIfTestRun("WARNING: %s" % message)
    elif not SETTINGS.filters.useIncludesFile \
            and SETTINGS.filters.useExcludesFile:
        message = "Files matching patterns in excludes " \
            "file will not be scanned for upload."
        logger.warning(message)
        LogIfTestRun("WARNING: %s" % message)
    elif SETTINGS.filters.useIncludesFile \
            and SETTINGS.filters.useExcludesFile:
        message = "Files matching patterns in excludes " \
            "file will not be scanned for upload, " \
            "unless they match patterns in the includes file."
        logger.warning(message)
        LogIfTestRun("WARNING: %s" % message)
    CheckDataFileGlobFiles(setStatusMessage)


def CheckDataFileGlobFiles(setStatusMessage):
    """
    Check includes and excludes files
    """
    from ...settings import SETTINGS

    if SETTINGS.filters.useIncludesFile:
        message = "Settings validation - checking includes file..."
        logger.debug(message)
        if setStatusMessage:
            setStatusMessage(message)
        PerformGlobsFileValidation(SETTINGS.filters.includesFile,
                                   "Includes", "includes", "includes_file")

    CheckIfShouldAbort(setStatusMessage)

    if SETTINGS.filters.useExcludesFile:
        message = "Settings validation - checking excludes file..."
        logger.debug(message)
        if setStatusMessage:
            setStatusMessage(message)
        PerformGlobsFileValidation(SETTINGS.filters.excludesFile,
                                   "Excludes", "excludes", "excludes_file")


def CheckMyTardisUrl(setStatusMessage, testRun):
    """
    Check MyTardis URL
    """
    from ...settings import SETTINGS

    def LogIfTestRun(message):
        """
        Log message if this is a Test Run
        """
        if testRun:
            logger.testrun(message)

    try:
        message = "Settings validation - checking MyTardis URL..."
        logger.debug(message)
        if setStatusMessage:
            setStatusMessage(message)
        response = requests.get(SETTINGS.general.myTardisApiUrl,
                                timeout=DEFAULT_TIMEOUT)
        history = response.history
        url = response.url
        if history:
            message = "MyData attempted to access MyTardis at " \
                "\"%s\", but was redirected to:" \
                "\n\n" % SETTINGS.general.myTardisApiUrl
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
            raise InvalidSettings(message, "mytardis_url")
        elif response.status_code == 200:
            message = "Retrieved %s in %.3f seconds." \
                % (SETTINGS.general.myTardisApiUrl,
                   response.elapsed.total_seconds())
            logger.debug(message)
            LogIfTestRun(message)
        elif response.status_code < 200 or response.status_code >= 300:
            logger.debug("Received HTTP %d while trying to access "
                         "MyTardis server (%s)."
                         % (response.status_code,
                            SETTINGS.general.myTardisUrl))
            message = (
                "Please enter a valid MyTardis URL.\n\n"
                "Received HTTP status code %d" % response.status_code)
            LogIfTestRun("ERROR: %s" % message)
            raise InvalidSettings(message, "mytardis_url")
    except requests.exceptions.Timeout:
        message = "Attempt to connect to %s timed out after " \
            "%s seconds." % (SETTINGS.general.myTardisApiUrl, DEFAULT_TIMEOUT)
        LogIfTestRun("ERROR: %s" % message)
        logger.error(traceback.format_exc())
        raise InvalidSettings(message, "mytardis_url")
    except requests.exceptions.InvalidSchema as err:
        message = (
            "Please enter a valid MyTardis URL, "
            "beginning with \"http://\" or \"https://\".\n\n"
            "%s" % str(err))
        LogIfTestRun("ERROR: %s" % message)
        if not SETTINGS.general.myTardisUrl.startswith("http"):
            suggestion = "http://" + SETTINGS.general.myTardisUrl
        else:
            suggestion = None
        raise InvalidSettings(message, "mytardis_url", suggestion)
    except requests.exceptions.RequestException as err:
        logger.error(traceback.format_exc())
        message = (
            "Please enter a valid MyTardis URL.\n\n"
            "%s" % str(err))
        LogIfTestRun("ERROR: %s" % message)
        raise InvalidSettings(message, "mytardis_url")


def CheckMyTardisCredentials(setStatusMessage):
    """
    Check MyTardis credentials

    Here we run an arbitrary query, to test whether
    our MyTardis credentials work OK with the API.
    """
    from ...settings import SETTINGS
    message = "Settings validation - checking MyTardis credentials..."
    logger.debug(message)
    if setStatusMessage:
        setStatusMessage(message)
    url = SETTINGS.general.myTardisUrl + \
        "/api/v1/user/?format=json&username=" + SETTINGS.general.username
    response = requests.get(headers=SETTINGS.defaultHeaders, url=url)
    statusCode = response.status_code
    if statusCode < 200 or statusCode >= 300:
        message = "Your MyTardis credentials are invalid.\n\n" \
            "Please check your Username and API Key."
        raise InvalidSettings(message, "username")


def CheckFacility(setStatusMessage):
    """
    Check facility
    """
    from ...settings import SETTINGS
    message = "Settings validation - checking MyTardis facility..."
    logger.debug(message)
    if setStatusMessage:
        setStatusMessage(message)
    if SETTINGS.general.facilityName.strip() == "":
        message = "Please enter a valid facility name."
        suggestion = None
        try:
            facilities = FacilityModel.GetMyFacilities()
            if len(facilities) == 1:
                suggestion = facilities[0].name
            raise InvalidSettings(message, "facility_name", suggestion)
        except:
            logger.error(traceback.format_exc())
            raise InvalidSettings(message, "facility_name")
    if SETTINGS.facility is None:
        facilities = FacilityModel.GetMyFacilities()
        message = "Facility \"%s\" was not found in MyTardis." \
            % SETTINGS.general.facilityName
        if len(facilities) > 0:
            message += "\n\n" + \
                "The facilities which user \"%s\" " \
                "has access to are:\n\n" % SETTINGS.general.username
            for facility in facilities:
                message = message + "    " + facility.name + "\n"
        else:
            message += "\n\n" + \
                "Please ask your MyTardis administrator to " \
                "ensure that the \"%s\" facility exists and that " \
                "user \"%s\" is a member of the managers group for " \
                "that facility." \
                % (SETTINGS.general.facilityName,
                   SETTINGS.general.username)
        suggestion = None
        if len(facilities) == 1:
            suggestion = facilities[0].name
        raise InvalidSettings(message, "facility_name", suggestion)


def CheckInstrument(setStatusMessage):
    """
    Check instrument
    """
    from ...settings import SETTINGS
    message = "Settings validation - checking instrument name..."
    logger.debug(message)
    if setStatusMessage:
        setStatusMessage(message)
    try:
        # Try to get the InstrumentModel from the instrument name:
        _ = SETTINGS.instrument
    except Unauthorized as err:
        message = str(err)
        raise InvalidSettings(message, "instrument_name")


def CheckContactEmailAndEmailFolders(setStatusMessage):
    """
    Check contact email and email folders
    """
    from ...settings import SETTINGS
    message = "Settings validation - validating email address..."
    logger.debug(message)
    if setStatusMessage:
        setStatusMessage(message)

    if not validate_email(SETTINGS.general.contactEmail):
        message = "Please enter a valid contact email."
        raise InvalidSettings(message, "contact_email")
    if SETTINGS.advanced.folderStructure.startswith('Email'):
        dataDir = SETTINGS.general.dataDirectory
        folderNames = os.walk(dataDir).next()[1]
        for folderName in folderNames:
            if not validate_email(folderName):
                message = "Folder name \"%s\" in \"%s\" is not a " \
                    "valid email address." % (folderName, dataDir)
                raise InvalidSettings(message, "data_directory")


def CheckAutostart(setStatusMessage):
    """
    Check if MyData is configured to start automatically

    On Windows, this is done at install time by the setup wizard.

    On macOS and Linux, this is done within the individual user's
    home directory, so it needs to be done the first time MyData
    runs, and after the start automatically checkbox value changes.

    If SETTINGS.advanced.startAutomaticallyOnLogin hasn't changed since the
    last check in this MyData session, then we don't update the autostart file,
    because doing so can be time-consuming.
    See: mydata.utils.autostart.UpdateMacAutostartFile
    """
    from ...settings import SETTINGS
    if SETTINGS.lastCheckedAutostartValue != \
            SETTINGS.advanced.startAutomaticallyOnLogin:
        message = "Settings validation - " \
            "checking if MyData is set to start automatically..."
        logger.debug(message)
        if setStatusMessage:
            setStatusMessage(message)
        UpdateAutostartFile()


def CheckScheduledTime():
    """
    Check scheduled time
    """
    from ...settings import SETTINGS
    if SETTINGS.schedule.scheduleType == "Once":
        dateTime = datetime.combine(SETTINGS.schedule.scheduledDate,
                                    SETTINGS.schedule.scheduledTime)
        if dateTime < datetime.now():
            message = "Scheduled time is in the past."
            raise InvalidSettings(message, "scheduled_time")


def PerformGlobsFileValidation(filePath, upper, lower, field):
    """
    Used to validate an "includes" or "excludes"
    file which is used to match file patterns,
    e.g. "*.txt"

    upper is an uppercase description of the glob file.
    lower is a lowercase description of the glob file.
    field
    """
    if filePath.strip() == "":
        message = "No %s file was specified." % lower
        raise InvalidSettings(message, field)
    if not os.path.exists(filePath):
        message = "Specified %s file doesn't exist." \
            % lower
        raise InvalidSettings(message, field)
    if not os.path.isfile(filePath):
        message = "Specified %s file path is not a file." \
            % lower
        raise InvalidSettings(message, field)
    with open(filePath, 'r') as globsFile:
        for line in globsFile.readlines():
            try:
                # Lines starting with '#' or ';' will be ignored.
                # Other non-blank lines are expected to be globs,
                # e.g. *.txt
                _ = line.decode('utf-8').strip()
            except UnicodeDecodeError:
                message = "%s file is not a valid plain text " \
                    "(UTF-8) file." % upper
                raise InvalidSettings(message, field)


def CheckStructureAndCountDatasets(setStatusMessage=None):
    """
    Counts datasets, while traversing the folder structure.  Previous versions
    of this method would alert the user about missing folders.

    The missing folder alerts have been removed, so the primary purpose of
    this method is to count datasets, although the Settings dialog checkbox
    which enables it is still called "Validate folder structure"
    """
    from ...settings import SETTINGS
    message = "Settings validation - checking folder structure..."
    logger.debug(message)
    if setStatusMessage:
        setStatusMessage(message)
    dataDirectory = SETTINGS.general.dataDirectory
    levels = len(SETTINGS.advanced.folderStructure.split('/'))
    datasetCount = -1
    folderGlobs = []
    for level in range(1, levels + 1):
        folderGlobs.append(FolderGlob(level))
        files = glob(os.path.join(dataDirectory, *folderGlobs))
        dirs = [item for item in files if os.path.isdir(item)]
        if level == levels:
            datasetCount = CountDatasetsInDirs(dirs)

    return datasetCount


def CountDatasetsInDirs(dirs):
    """
    :param dirs: List of absolute directory paths which could be dataset
                 folders, depending on the active dataset filter(s)
    """
    from ...settings import SETTINGS
    seconds = dict(day=24 * 60 * 60)
    seconds['year'] = int(365.25 * seconds['day'])
    seconds['month'] = seconds['year'] / 12
    singularIgnoreIntervalUnit = \
        SETTINGS.filters.ignoreOldDatasetIntervalUnit.rstrip('s')
    ignoreIntervalUnitSeconds = seconds[singularIgnoreIntervalUnit]
    ignoreIntervalSeconds = (
        SETTINGS.filters.ignoreOldDatasetIntervalNumber *
        ignoreIntervalUnitSeconds)

    if SETTINGS.filters.ignoreOldDatasets:
        datasetCount = 0
        for folder in dirs:
            ctimestamp = os.path.getctime(folder)
            ctime = datetime.fromtimestamp(ctimestamp)
            age = datetime.now() - ctime
            if age.total_seconds() <= ignoreIntervalSeconds:
                datasetCount += 1
    else:
        datasetCount = len(dirs)
    return datasetCount


def FolderGlob(level, instrumentName='*'):
    """
    Get the glob used to restrict folders at a certain level, based on filters
    specified in settings.

    :param level: Folder level (1 for folders which are direct children of
                  SETTINGS.general.dataDirectory, 2 for grandchildren etc.)
    """
    from ...settings import SETTINGS
    userOrGroupGlob = "*%s*" % SETTINGS.filters.userFilter
    datasetGlob = "*%s*" % SETTINGS.filters.datasetFilter
    expGlob = "*%s*" % SETTINGS.filters.experimentFilter
    globDict = {
        'Dataset': [datasetGlob],
        'Username / Dataset': [userOrGroupGlob, datasetGlob],
        'User Group / Dataset':
            [userOrGroupGlob, datasetGlob],
        'Email / Dataset': [userOrGroupGlob, datasetGlob],
        'Experiment / Dataset': [expGlob, datasetGlob],
        'Username / Experiment / Dataset':
            [userOrGroupGlob, expGlob, datasetGlob],
        'User Group / Experiment / Dataset':
            [userOrGroupGlob, expGlob, datasetGlob],
        'Email / Experiment / Dataset':
            [userOrGroupGlob, expGlob, datasetGlob],
        'Username / "MyTardis" / Experiment / Dataset':
            [userOrGroupGlob, 'MyTardis', expGlob, datasetGlob],
        'User Group / Instrument / Full Name / Dataset':
            [userOrGroupGlob, instrumentName, '*', datasetGlob]
    }
    return globDict[SETTINGS.advanced.folderStructure][level - 1]


def CheckIfShouldAbort(setStatusMessage):
    """
    Check if settings validation should abort, because the user has clicked the
    Stop button on the main MyData frame's toolbar.  And if so, raise
    UserAbortedSettingsValidation
    """
    app = wx.GetApp()
    if hasattr(app, "ShouldAbort") and app.ShouldAbort():
        raise UserAbortedSettingsValidation(setStatusMessage)

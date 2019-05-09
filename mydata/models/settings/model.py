"""
Model class for the settings displayed in the settings dialog
and saved to disk in MyData.cfg
"""
import os
import pickle
import traceback

from six.moves import urllib

from ...constants import APPNAME
from ...logs import logger
from ...threads.locks import LOCKS
from ...utils import CreateConfigPathIfNecessary
from .general import GeneralSettingsModel
from .schedule import ScheduleSettingsModel
from .filters import FiltersSettingsModel
from .advanced import AdvancedSettingsModel
from .miscellaneous import MiscellaneousSettingsModel
from .miscellaneous import LastSettingsUpdateTrigger
from .serialize import LoadSettings


class SettingsModel(object):
    """
    Model class for the settings displayed in the settings dialog
    and saved to disk in MyData.cfg
    """
    def __init__(self, configPath, checkForUpdates=True):
        super(SettingsModel, self).__init__()

        # Previous settings, so we can roll back if validation fails:
        self.previous = dict(
            general=dict(mydataConfig=dict()),
            schedule=dict(mydataConfig=dict()),
            filters=dict(mydataConfig=dict()),
            advanced=dict(mydataConfig=dict()),
            miscellaneous=dict(mydataConfig=dict()),
            lastSettingsUpdateTrigger=None)

        # The location on disk of MyData.cfg
        # e.g. "C:\\ProgramData\\Monash University\\MyData\\MyData.cfg" or
        # "/Users/jsmith/Library/Application Support/MyData/MyData.cfg":
        self._configPath = configPath

        self.verifiedDatafilesCache = dict()

        self._uploaderModel = None

        self.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.READ_FROM_DISK

        self.models = dict(
            general=GeneralSettingsModel(),
            schedule=ScheduleSettingsModel(),
            filters=FiltersSettingsModel(),
            advanced=AdvancedSettingsModel(),
            miscellaneous=MiscellaneousSettingsModel())

        self.SetDefaultConfig()

        try:
            LoadSettings(self, checkForUpdates=checkForUpdates)
        except:
            logger.error(traceback.format_exc())

    @property
    def general(self):
        """
        Settings in the Settings Dialog's General tab
        """
        return self.models['general']

    @property
    def schedule(self):
        """
        Settings in the Settings Dialog's Schedule tab
        """
        return self.models['schedule']

    @property
    def filters(self):
        """
        Settings in the Settings Dialog's Filters tab
        """
        return self.models['filters']

    @property
    def advanced(self):
        """
        Settings in the Settings Dialog's Advanced tab
        """
        return self.models['advanced']

    @property
    def miscellaneous(self):
        """
        Miscellaneous settings
        """
        return self.models['miscellaneous']

    def __setitem__(self, key, item):
        """
        Set a config item by field name.
        """
        if key in self.general.fields:
            self.general.mydataConfig[key] = item
        elif key in self.schedule.fields:
            self.schedule.mydataConfig[key] = item
        elif key in self.filters.fields:
            self.filters.mydataConfig[key] = item
        elif key in self.advanced.fields:
            self.advanced.mydataConfig[key] = item
        elif key in self.miscellaneous.fields:
            self.miscellaneous.mydataConfig[key] = item
        else:
            raise KeyError(key)

    def __getitem__(self, key):
        """
        Get a config item by field name.
        """
        if key in self.general.fields:
            return self.general.mydataConfig[key]
        elif key in self.schedule.fields:
            return self.schedule.mydataConfig[key]
        elif key in self.filters.fields:
            return self.filters.mydataConfig[key]
        elif key in self.advanced.fields:
            return self.advanced.mydataConfig[key]
        elif key in self.miscellaneous.fields:
            return self.miscellaneous.mydataConfig[key]
        else:
            raise KeyError(key)

    @property
    def uploaderModel(self):
        """
        Get the uploader (MyData instance) model

        This could be called from multiple threads
        simultaneously, so it requires locking.
        """
        from ..uploader import UploaderModel
        if self._uploaderModel:
            return self._uploaderModel
        try:
            LOCKS.createUploader.acquire()
            self._uploaderModel = UploaderModel(self)
            return self._uploaderModel
        finally:
            LOCKS.createUploader.release()

    @uploaderModel.setter
    def uploaderModel(self, uploaderModel):
        """
        Set uploader model (representing this MyData instance)
        """
        self._uploaderModel = uploaderModel

    def Update(self, settings):
        """
        Update this instance from another
        """
        self.general.mydataConfig.update(settings.general.mydataConfig)
        self.schedule.mydataConfig.update(settings.schedule.mydataConfig)
        self.filters.mydataConfig.update(settings.filters.mydataConfig)
        self.advanced.mydataConfig.update(settings.advanced.mydataConfig)
        self.miscellaneous.mydataConfig.update(
            settings.miscellaneous.mydataConfig)
        self.lastSettingsUpdateTrigger = settings.lastSettingsUpdateTrigger

    def SavePrevious(self):
        """
        Save current settings to self.previous so we can roll back if necessary
        """
        self.previous['general']['mydataConfig'].update(
            self.general.mydataConfig)
        self.previous['schedule']['mydataConfig'].update(
            self.schedule.mydataConfig)
        self.previous['filters']['mydataConfig'].update(
            self.filters.mydataConfig)
        self.previous['advanced']['mydataConfig'].update(
            self.advanced.mydataConfig)
        self.previous['miscellaneous']['mydataConfig'].update(
            self.miscellaneous.mydataConfig)
        self.previous['lastSettingsUpdateTrigger'] = \
            self.lastSettingsUpdateTrigger

    def RollBack(self):
        """
        If settings validation fails, call this method to roll back the
        updates made to SETTINGS from SaveFieldsFromDialog.

        If a user changes a valid field to an invalid field in the Settings
        dialog and clicks OK, settings validation will fail, and the Settings
        dialog will remain open after displaying an error message.  In order
        for settings to be validated, they need to be saved from the Settings
        dialog to the SETTINGS SettingsModel instance(*).  If the user chooses
        not to correct the invalid field in the Settings dialog, they can
        click "Cancel" to close the Settings dialog.  The next time they open
        the Settings dialog, the last valid field value will be displayed,
        because the failed settings validation triggers a roll back.

        (*) In earlier code versions, fields from the Settings dialog were
        initially saved to a temporary SettingsModel instance, but it was
        decided that it was simpler to just have a single global SETTINGS
        instance which can be rolled back if necessary.
        """
        self.general.mydataConfig.update(
            self.previous['general']['mydataConfig'])
        self.schedule.mydataConfig.update(
            self.previous['schedule']['mydataConfig'])
        self.filters.mydataConfig.update(
            self.previous['filters']['mydataConfig'])
        self.advanced.mydataConfig.update(
            self.previous['advanced']['mydataConfig'])
        self.miscellaneous.mydataConfig.update(
            self.previous['miscellaneous']['mydataConfig'])
        self.lastSettingsUpdateTrigger = \
            self.previous['lastSettingsUpdateTrigger']

    def RequiredFieldIsBlank(self):
        """
        Return True if a required field is blank
        """
        return self.general.instrumentName == "" or \
            self.general.facilityName == "" or \
            self.general.contactName == "" or \
            self.general.contactEmail == "" or \
            self.general.dataDirectory == "" or \
            self.general.myTardisUrl == "" or \
            self.general.username == "" or \
            self.general.apiKey == ""

    def SetDefaultConfig(self):
        """
        Set default values for configuration parameters
        that will appear in MyData.cfg
        """
        self.general.SetDefaults()
        self.schedule.SetDefaults()
        self.filters.SetDefaults()
        self.advanced.SetDefaults()
        self.miscellaneous.SetDefaults()

    @property
    def defaultHeaders(self):
        """
        Default HTTP headers, providing authorization for MyTardis API.
        """
        return {
            "Authorization": "ApiKey %s:%s" % (self.general.username,
                                               self.general.apiKey),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    @property
    def verifiedDatafilesCachePath(self):
        """
        We use a serialized dictionary to cache DataFile lookup results.
        We'll use a separate cache file for each MyTardis server we connect to.
        """
        parsed = urllib.parse.urlparse(self.general.myTardisUrl)
        return os.path.join(
            os.path.dirname(self.configPath),
            "verified-files-%s-%s.pkl" %
            (parsed.scheme, parsed.netloc))

    def InitializeVerifiedDatafilesCache(self):
        """
        We use a serialized dictionary to cache DataFile lookup results.
        We'll use a separate cache file for each MyTardis server we connect to.
        """
        try:
            if os.path.exists(self.verifiedDatafilesCachePath):
                with open(self.verifiedDatafilesCachePath, 'rb') as cacheFile:
                    self.verifiedDatafilesCache = pickle.load(cacheFile)
            else:
                self.verifiedDatafilesCache = dict()
        except:
            self.verifiedDatafilesCache = dict()
            logger.warning(traceback.format_exc())

    def SaveVerifiedDatafilesCache(self):
        """
        We use a serialized dictionary to cache DataFile lookup results.
        We'll use a separate cache file for each MyTardis server we connect to.
        """
        with LOCKS.closeCache:
            try:
                with open(self.verifiedDatafilesCachePath,
                          'wb') as cacheFile:
                    pickle.dump(self.verifiedDatafilesCache, cacheFile)
            except:
                logger.warning("Couldn't save verified datafiles cache.")
                logger.warning(traceback.format_exc())

    @property
    def configPath(self):
        """
        The location on disk of MyData.cfg
        e.g. "C:\\ProgramData\\Monash University\\MyData\\MyData.cfg" or
        "/Users/jsmith/Library/Application Support/MyData/MyData.cfg"
        """
        if not self._configPath:
            appdirPath = CreateConfigPathIfNecessary()
            self._configPath = os.path.join(appdirPath, APPNAME + '.cfg')
        return self._configPath

    @configPath.setter
    def configPath(self, configPath):
        """
        The location on disk of MyData.cfg
        e.g. "C:\\ProgramData\\Monash University\\MyData\\MyData.cfg" or
        "/Users/jsmith/Library/Application Support/MyData/MyData.cfg"
        """
        self._configPath = configPath

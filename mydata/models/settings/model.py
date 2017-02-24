"""
Model class for the settings displayed in the settings dialog
and saved to disk in MyData.cfg
"""
import traceback
import threading

from ...logs import logger
from ...utils.exceptions import DuplicateKey
from ...utils.exceptions import DoesNotExist
from ..facility import FacilityModel
from ..instrument import InstrumentModel
from ..uploader import UploaderModel
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
    # pylint: disable=too-many-instance-attributes
    def __init__(self, configPath, checkForUpdates=True):
        super(SettingsModel, self).__init__()

        self.previousDict = {}

        self.configPath = configPath

        self._uploaderModel = None
        self.uploadToStagingRequest = None
        self.sshKeyPair = None

        self.lastSettingsUpdateTrigger = \
            LastSettingsUpdateTrigger.READ_FROM_DISK

        self.connectivityCheckInterval = 30  # seconds

        self.general = GeneralSettingsModel(self)
        self.schedule = ScheduleSettingsModel()
        self.filters = FiltersSettingsModel()
        self.advanced = AdvancedSettingsModel()
        self.miscellaneous = MiscellaneousSettingsModel()

        self.SetDefaultConfig()

        self.createUploaderThreadingLock = threading.Lock()

        try:
            LoadSettings(self, checkForUpdates=checkForUpdates)
        except:
            logger.error(traceback.format_exc())

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
    def facility(self):
        """
        Return the FacilityModel for the specified facility name
        """
        return self.general.facility

    @property
    def instrument(self):
        """
        Return the InstrumentModel for the specified instrument name
        """
        return self.general.instrument

    @property
    def defaultOwner(self):
        """
        Get user model for the specified MyTardis username
        """
        return self.general.defaultOwner

    @defaultOwner.setter
    def defaultOwner(self, defaultOwner):
        """
        Set default user model for assigning experiment ACLs.
        Only used by tests.
        """
        self.general.defaultOwner = defaultOwner

    @property
    def uploaderModel(self):
        """
        Get the uploader (MyData instance) model

        This could be called from multiple threads
        simultaneously, so it requires locking.
        """
        if self._uploaderModel:
            return self._uploaderModel
        try:
            self.createUploaderThreadingLock.acquire()
            self._uploaderModel = UploaderModel(self)
            return self._uploaderModel
        finally:
            self.createUploaderThreadingLock.release()

    @uploaderModel.setter
    def uploaderModel(self, uploaderModel):
        """
        Set uploader model (representing this MyData instance)
        """
        self._uploaderModel = uploaderModel

    def RollBack(self):
        """
        If settings validation fails, call this method to roll back
        the updates made to settings from SaveFieldsFromDialog.
        """
        self.__dict__.update(self.previousDict)

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

    def RenameInstrument(self, facilityName,
                         oldInstrumentName, newInstrumentName):
        """
        Rename the instrument
        """
        facilities = FacilityModel.GetMyFacilities(self)
        facility = None
        for facil in facilities:
            if facilityName == facil.GetName():
                facility = facil
                break
        if facility is None:
            raise Exception("Facility is None in "
                            "SettingsModel's RenameInstrument.")
        try:
            oldInstrument = \
                InstrumentModel.GetInstrument(self, facility, oldInstrumentName)
        except DoesNotExist:
            raise Exception("Instrument record for old instrument "
                            "name not found in SettingsModel's "
                            "RenameInstrument.")
        try:
            _ = InstrumentModel.GetInstrument(self, facility,
                                              newInstrumentName)
            raise DuplicateKey(
                message="Instrument with name \"%s\" "
                        "already exists" % newInstrumentName)
        except DoesNotExist:
            oldInstrument.Rename(newInstrumentName)

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
        self._defaultOwner = None
        self._instrument = None
        self._facility = None

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

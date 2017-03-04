"""
Model class for the settings displayed in the General tab
of the settings dialog and saved to disk in MyData.cfg
"""
from ...logs import logger
from ...utils.exceptions import DoesNotExist


class GeneralSettingsModel(object):
    """
    Model class for the settings displayed in the General tab
    of the settings dialog and saved to disk in MyData.cfg
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        # Saved in MyData.cfg:
        self.mydataConfig = dict()
        self.fields = [
            'instrument_name',
            'facility_name',
            'contact_name',
            'contact_email',
            'data_directory',
            'mytardis_url',
            'username',
            'api_key'
        ]
        self._defaultOwner = None
        self._instrument = None
        self._facility = None

    @property
    def instrumentName(self):
        """
        Get instrument name
        """
        return self.mydataConfig['instrument_name']

    @instrumentName.setter
    def instrumentName(self, instrumentName):
        """
        Set instrument name
        """
        self.mydataConfig['instrument_name'] = instrumentName
        self._instrument = None

    @property
    def instrument(self):
        """
        Return the InstrumentModel for the specified instrument name
        """
        from ..instrument import InstrumentModel
        if self._instrument:
            return self._instrument
        try:
            self._instrument = InstrumentModel.GetInstrument(
                self.facility, self.instrumentName)
        except DoesNotExist:
            logger.info("No instrument record with name \"%s\" was found "
                        "in facility \"%s\", so we will create one."
                        % (self.instrumentName, self.facilityName))
            self._instrument = InstrumentModel.CreateInstrument(
                self.facility, self.instrumentName)
        return self._instrument

    @property
    def facilityName(self):
        """
        Get facility name
        """
        return self.mydataConfig['facility_name']

    @facilityName.setter
    def facilityName(self, facilityName):
        """
        Set facility name
        """
        self.mydataConfig['facility_name'] = facilityName
        self._facility = None

    @property
    def facility(self):
        """
        Return the FacilityModel for the specified facility name
        """
        from ..facility import FacilityModel
        if self._facility:
            return self._facility
        facilities = FacilityModel.GetMyFacilities()
        for facility in facilities:
            if self.facilityName == facility.name:
                self._facility = facility
        return self._facility

    @property
    def contactName(self):
        """
        Get contact name
        """
        return self.mydataConfig['contact_name']

    @contactName.setter
    def contactName(self, contactName):
        """
        Set contact name
        """
        self.mydataConfig['contact_name'] = contactName

    @property
    def contactEmail(self):
        """
        Set contact email
        """
        return self.mydataConfig['contact_email']

    @contactEmail.setter
    def contactEmail(self, contactEmail):
        """
        Set contact email
        """
        self.mydataConfig['contact_email'] = contactEmail

    @property
    def dataDirectory(self):
        """
        Get root data directory
        """
        return self.mydataConfig['data_directory']

    @dataDirectory.setter
    def dataDirectory(self, dataDirectory):
        """
        Set root data directory
        """
        self.mydataConfig['data_directory'] = dataDirectory

    @property
    def myTardisUrl(self):
        """
        Get MyTardis URL
        """
        return self.mydataConfig['mytardis_url']

    @property
    def myTardisApiUrl(self):
        """
        Get MyTardis API URL
        """
        return self.mydataConfig['mytardis_url'] + "/api/v1/?format=json"

    @myTardisUrl.setter
    def myTardisUrl(self, myTardisUrl):
        """
        Set MyTardis API URL
        """
        self.mydataConfig['mytardis_url'] = myTardisUrl.rstrip('/')
        self._defaultOwner = None
        self._instrument = None
        self._facility = None

    @property
    def username(self):
        """
        Get MyTardis username (should be a facility manager)
        """
        return self.mydataConfig['username']

    @username.setter
    def username(self, username):
        """
        Set MyTardis username (should be a facility manager)
        """
        self.mydataConfig['username'] = username
        self._defaultOwner = None
        self._instrument = None
        self._facility = None

    @property
    def defaultOwner(self):
        """
        Get user model for the specified MyTardis username
        """
        from ..user import UserModel
        if not self._defaultOwner:
            self._defaultOwner = UserModel.GetUserByUsername(self.username)
        return self._defaultOwner

    @defaultOwner.setter
    def defaultOwner(self, defaultOwner):
        """
        Set default user model for assigning experiment ACLs.
        Only used by tests.
        """
        self._defaultOwner = defaultOwner

    @property
    def apiKey(self):
        """
        Get API key
        """
        return self.mydataConfig['api_key']

    @apiKey.setter
    def apiKey(self, apiKey):
        """
        Set API key
        """
        self.mydataConfig['api_key'] = apiKey
        self._defaultOwner = None
        self._instrument = None
        self._facility = None

    def SetDefaults(self):
        """
        Set default values for configuration parameters
        that will appear in MyData.cfg for fields in the
        Settings Dialog's General tab
        """
        self.mydataConfig['facility_name'] = ""
        self.mydataConfig['instrument_name'] = ""
        self.mydataConfig['contact_name'] = ""
        self.mydataConfig['contact_email'] = ""
        self.mydataConfig['data_directory'] = ""
        self.mydataConfig['mytardis_url'] = ""
        self.mydataConfig['username'] = ""
        self.mydataConfig['api_key'] = ""

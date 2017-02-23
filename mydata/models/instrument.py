"""
Model class for MyTardis API v1's InstrumentResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import json
import urllib
import requests

from mydata.logs import logger
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import Unauthorized
from .facility import FacilityModel
from . import HandleHttpError


class InstrumentModel(object):
    """
    Model class for MyTardis API v1's InstrumentResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    def __init__(self, settingsModel, name, instrumentJson):

        self.settingsModel = settingsModel
        self.name = name
        self.json = instrumentJson
        self.instrumentId = instrumentJson['id']
        self.facility = FacilityModel(
            facilityJson=instrumentJson['facility'])

    def __str__(self):
        return "InstrumentModel " + self.name + \
            " - " + self.GetFacility().GetName()

    def GetId(self):
        """
        Return the instrument ID.
        """
        return self.instrumentId

    def GetName(self):
        """
        Return the instrument name.
        """
        return self.name

    def GetFacility(self):
        """
        Return the facility.
        """
        return self.facility

    def GetResourceUri(self):
        """
        Return the API resource URI..
        """
        return self.json['resource_uri']

    @staticmethod
    def CreateInstrument(settings, facility, name):
        """
        Create instrument.
        """
        url = "%s/api/v1/instrument/" % settings.general.myTardisUrl
        instrumentJson = {
            "facility": facility.GetResourceUri(),
            "name": name}
        data = json.dumps(instrumentJson)
        headers = settings.defaultHeaders
        response = requests.post(headers=headers, url=url, data=data)
        if response.status_code == 201:
            instrumentJson = response.json()
            return InstrumentModel(settingsModel=settings, name=name,
                                   instrumentJson=instrumentJson)
        else:
            if response.status_code == 401:
                message = "Couldn't create instrument \"%s\" " \
                          "in facility \"%s\"." \
                          % (name, facility.GetName())
                message += "\n\n"
                message += "Please ask your MyTardis administrator to " \
                           "check the permissions of the \"%s\" " \
                           "user account." % settings.general.username
                raise Unauthorized(message)
            HandleHttpError(response)

    @staticmethod
    def GetInstrument(settings, facility, name):
        """
        Get instrument.
        """
        url = "%s/api/v1/instrument/?format=json&facility__id=%s&name=%s" \
            % (settings.general.myTardisUrl, facility.GetId(),
               urllib.quote(name.encode('utf-8')))
        response = requests.get(url=url, headers=settings.defaultHeaders)
        if response.status_code != 200:
            HandleHttpError(response)
        instrumentsJson = response.json()
        numInstrumentsFound = \
            instrumentsJson['meta']['total_count']
        if numInstrumentsFound == 0:
            message = "Instrument \"%s\" was not found in MyTardis" % name
            logger.warning(message)
            raise DoesNotExist(message, response, modelClass=InstrumentModel)
        else:
            logger.debug("Found instrument record for name \"%s\" "
                         "in facility \"%s\"" %
                         (name, facility.GetName()))
            instrumentJson = instrumentsJson['objects'][0]
            return InstrumentModel(
                settingsModel=settings, name=name,
                instrumentJson=instrumentJson)

    def Rename(self, name):
        """
        Rename instrument.
        """
        logger.info("Renaming instrument \"%s\" to \"%s\"."
                    % (str(self), name))
        url = "%s/api/v1/instrument/%d/" \
            % (self.settingsModel.general.myTardisUrl, self.GetId())
        uploaderJson = {"name": name}
        data = json.dumps(uploaderJson)
        headers = self.settingsModel.defaultHeaders
        response = requests.put(headers=headers, url=url, data=data)
        if response.status_code == 200:
            logger.info("Renaming instrument succeeded.")
        else:
            HandleHttpError(response)

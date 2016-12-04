"""
Model class for MyTardis API v1's InstrumentResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import json
import urllib
import requests

from mydata.logs import logger
from mydata.utils.exceptions import Unauthorized
from .facility import FacilityModel


class InstrumentModel(object):
    """
    Model class for MyTardis API v1's InstrumentResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    def __init__(self, settingsModel=None, name=None,
                 instrumentJson=None):

        self.settingsModel = settingsModel
        self.instrumentId = None
        self.name = name
        self.json = instrumentJson
        self.facility = None

        if instrumentJson is not None:
            self.instrumentId = instrumentJson['id']
            if name is None:
                self.name = instrumentJson['name']
            self.facility = FacilityModel(
                facilityJson=instrumentJson['facility'])

    def __str__(self):
        return "InstrumentModel " + self.name + \
            " - " + self.GetFacility().GetName()

    def __repr__(self):
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

    def GetValueForKey(self, key):
        """
        Get value for key.
        """
        return self.__dict__[key]

    def GetJson(self):
        """
        Return JSON representation.
        """
        return self.json

    @staticmethod
    def CreateInstrument(settingsModel, facility, name):
        """
        Create instrument.
        """
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()
        url = myTardisUrl + "/api/v1/instrument/"
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey),
            "Content-Type": "application/json",
            "Accept": "application/json"}
        instrumentJson = {
            "facility": facility.GetResourceUri(),
            "name": name}
        data = json.dumps(instrumentJson)
        response = requests.post(headers=headers, url=url, data=data)
        content = response.text
        if response.status_code >= 200 and response.status_code < 300:
            instrumentJson = response.json()
            return InstrumentModel(settingsModel=settingsModel, name=name,
                                   instrumentJson=instrumentJson)
        else:
            if response.status_code == 401:
                message = "Couldn't create instrument \"%s\" " \
                          "in facility \"%s\"." \
                          % (name, facility.GetName())
                message += "\n\n"
                message += "Please ask your MyTardis administrator to " \
                           "check the permissions of the \"%s\" " \
                           "user account." % myTardisUsername
                raise Unauthorized(message)
            if response.status_code == 404:
                raise Exception("HTTP 404 (Not Found) received for: " + url)
            logger.error("Status code = " + str(response.status_code))
            logger.error("URL = " + url)
            raise Exception(content)

    @staticmethod
    def GetInstrument(settingsModel, facility, name):
        """
        Get instrument.
        """
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()
        url = myTardisUrl + "/api/v1/instrument/?format=json" + \
            "&facility__id=" + str(facility.GetId()) + \
            "&name=" + urllib.quote(name)
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey)}
        session = requests.Session()
        response = session.get(url=url, headers=headers)
        if response.status_code != 200:
            message = response.text
            logger.error(message)
            raise Exception(message)
        instrumentsJson = response.json()
        numInstrumentsFound = \
            instrumentsJson['meta']['total_count']
        if numInstrumentsFound == 0:
            logger.warning("Instrument \"%s\" was not found in MyTardis"
                           % name)
            logger.debug(url)
            logger.debug(response.text)
            response.close()
            session.close()
            return None
        else:
            logger.debug("Found instrument record for name \"%s\" "
                         "in facility \"%s\"" %
                         (name, facility.GetName()))
            instrumentJson = instrumentsJson['objects'][0]
            response.close()
            session.close()
            return InstrumentModel(
                settingsModel=settingsModel, name=name,
                instrumentJson=instrumentJson)

    def Rename(self, name):
        """
        Rename instrument.
        """
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        myTardisUsername = self.settingsModel.GetUsername()
        myTardisApiKey = self.settingsModel.GetApiKey()
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey),
            "Content-Type": "application/json",
            "Accept": "application/json"}
        logger.info("Renaming instrument \"%s\" to \"%s\"."
                    % (str(self), name))
        url = myTardisUrl + "/api/v1/instrument/%d/" % self.GetId()
        uploaderJson = {"name": name}
        data = json.dumps(uploaderJson)
        response = requests.put(headers=headers, url=url, data=data)
        if response.status_code >= 200 and response.status_code < 300:
            logger.info("Renaming instrument succeeded.")
        else:
            logger.info("Renaming instrument failed.")
            logger.info("Status code = " + str(response.status_code))
            logger.info(response.text)
        response.close()

    def GetSettingsModel(self):
        """
        Return settings model.
        """
        return self.settingsModel

    def SetSettingsModel(self, settingsModel):
        """
        Set settings model.
        """
        self.settingsModel = settingsModel

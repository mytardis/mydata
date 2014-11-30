import requests
import json
import urllib

from logger.Logger import logger
from FacilityModel import FacilityModel
from Exceptions import Unauthorized


class InstrumentModel():

    def __init__(self, settingsModel=None, name=None,
                 instrumentJson=None):

        self.settingsModel = settingsModel
        self.id = None
        self.name = name
        self.json = instrumentJson
        self.facility = None

        if instrumentJson is not None:
            self.id = instrumentJson['id']
            if name is None:
                self.name = instrumentJson['name']
            self.facility = FacilityModel(
                facilityJson=instrumentJson['facility'])

    def __str__(self):
        return "InstrumentModel " + self.name + \
            " - " + self.GetFacility().GetName()

    def __unicode__(self):
        return "InstrumentModel " + self.name + \
            " - " + self.GetFacility().GetName()

    def __repr__(self):
        return "InstrumentModel " + self.name + \
            " - " + self.GetFacility().GetName()

    def GetId(self):
        return self.id

    def GetName(self):
        return self.name

    def GetFacility(self):
        return self.facility

    def GetResourceUri(self):
        return self.json['resource_uri']

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetJson(self):
        return self.json

    @staticmethod
    def CreateInstrument(settingsModel, facility, name):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = settingsModel.GetUsername()
        myTardisDefaultUserApiKey = settingsModel.GetApiKey()
        url = myTardisUrl + "/api/v1/instrument/"
        headers = {"Authorization": "ApiKey " + myTardisDefaultUsername + ":" +
                   myTardisDefaultUserApiKey,
                   "Content-Type": "application/json",
                   "Accept": "application/json"}
        instrumentJson = \
            {"facility": facility.GetResourceUri(),
             "name": name}
        data = json.dumps(instrumentJson)
        response = requests.post(headers=headers, url=url, data=data)
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
                           "user account." % myTardisDefaultUsername
                raise Unauthorized(message)
            if response.status_code == 404:
                raise Exception("HTTP 404 (Not Found) received for: " + url)
            logger.error("Status code = " + str(response.status_code))
            logger.error("URL = " + url)
            raise Exception(response.text)

    @staticmethod
    def GetInstrument(settingsModel, facility, name):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()
        url = myTardisUrl + "/api/v1/instrument/?format=json" + \
            "&facility__id=" + str(facility.GetId()) + \
            "&name=" + urllib.quote(name)
        headers = {"Authorization": "ApiKey " + myTardisUsername + ":" +
                   myTardisApiKey}
        response = requests.get(url=url, headers=headers)
        if response.status_code != 200:
            logger.debug("Failed to look up instrument \"%s\" "
                         "in facility \"%s\"."
                         % (name, facility.GetName()))
            logger.debug(response.text)
            return None
        instrumentsJson = response.json()
        numInstrumentsFound = \
            instrumentsJson['meta']['total_count']
        if numInstrumentsFound == 0:
            logger.warning("Instrument \"%s\" was not found in MyTardis"
                           % name)
            logger.debug(url)
            logger.debug(response.text)
            return None
        else:
            logger.debug("Found instrument record for name \"%s\" "
                         "in facility \"%s\"" %
                         (name, facility.GetName()))
            return InstrumentModel(
                settingsModel=settingsModel, name=name,
                instrumentJson=instrumentsJson['objects'][0])

    @staticmethod
    def GetMyInstruments(settingsModel, userModel):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        instruments = []

        myFacilities = FacilityModel.GetMyFacilities(settingsModel, userModel)

        for facility in myFacilities:
            url = myTardisUrl + "/api/v1/instrument/?format=json" + \
                "&facility__id=" + str(facility.GetId())
            headers = {'Authorization': 'ApiKey ' + myTardisUsername + ":" +
                       myTardisApiKey}
            response = requests.get(url=url, headers=headers)
            if response.status_code != 200:
                logger.debug("Failed to look up instrument record for "
                             "facility \"" + facility.GetName() + "\".")
                logger.debug(response.text)
                return None
            instrumentsJson = response.json()
            for instrumentJson in instrumentsJson['objects']:
                instruments.append(InstrumentModel(
                    settingsModel=settingsModel,
                    instrumentJson=instrumentJson))

        return instruments

    def Rename(self, name):
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = self.settingsModel.GetUsername()
        myTardisDefaultUserApiKey = self.settingsModel.GetApiKey()
        headers = {"Authorization": "ApiKey " + myTardisDefaultUsername + ":" +
                   myTardisDefaultUserApiKey,
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

import requests
import json
import urllib

from logger.Logger import logger
from GroupModel import GroupModel


class FacilityModel():

    def __init__(self, settingsModel=None, name=None,
                 facilityJson=None):

        self.settingsModel = settingsModel
        self.id = None
        self.name = name
        self.json = facilityJson
        self.manager_group = None

        if facilityJson is not None:
            self.id = facilityJson['id']
            if name is None:
                self.name = facilityJson['name']
            self.manager_group = \
                GroupModel(groupJson=facilityJson['manager_group'])

    def __str__(self):
        return "FacilityModel " + self.name

    def __unicode__(self):
        return "FacilityModel " + self.name

    def __repr__(self):
        return "FacilityModel " + self.name

    def GetId(self):
        return self.id

    def GetName(self):
        return self.name

    def GetManagerGroup(self):
        return self.manager_group

    def GetResourceUri(self):
        return self.json['resource_uri']

    def GetValueForKey(self, key):
        return self.__dict__[key]

    def GetJson(self):
        return self.json

    @staticmethod
    def GetFacility(settingsModel, name):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/facility/?format=json&name=" + \
            urllib.quote(name)
        headers = {'Authorization': 'ApiKey ' + myTardisUsername + ":" +
                   myTardisApiKey}
        session = requests.Session()
        response = session.get(url=url, headers=headers, stream=False)
        logger.debug(response.text)
        if response.status_code != 200:
            message = response.text
            response.close()
            session.close()
            raise Exception(message)
        facilitiesJson = response.json()
        response.close()
        session.close()
        numFacilitysFound = facilitiesJson['meta']['total_count']

        if numFacilitysFound == 0:
            logger.warning("Facility \"%s\" was not found in MyTardis" % name)
            return None
        else:
            logger.debug("Found facility record for name '" + name + "'.")
            return FacilityModel(
                settingsModel=settingsModel, name=name,
                facilityJson=facilitiesJson['objects'][0])

    @staticmethod
    def GetMyFacilities(settingsModel, userModel):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        facilities = []

        groups = userModel.GetGroups()

        for group in groups:
            url = myTardisUrl + "/api/v1/facility/?format=json" + \
                "&manager_group__id=" + str(group.GetId())
            headers = {'Authorization': 'ApiKey ' + myTardisUsername + ":" +
                       myTardisApiKey}
            session = requests.Session()
            response = session.get(url=url, headers=headers)
            if response.status_code != 200:
                message = response.text
                response.close()
                session.close()
                raise Exception(message)
            response.close()
            session.close()
            facilitiesJson = response.json()
            for facilityJson in facilitiesJson['objects']:
                facilities.append(FacilityModel(
                    settingsModel=settingsModel,
                    facilityJson=facilityJson))

        return facilities

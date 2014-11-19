import requests
import json
import urllib

from logger.Logger import logger
from GroupModel import GroupModel

class FacilityModel():

    def __init__(self, settingsModel=None, id=None, name=None,
                 facilityRecordJson=None):

        self.settingsModel = settingsModel
        self.id = id
        self.name = name
        self.json = facilityRecordJson
        self.manager_group = None

        if facilityRecordJson is not None:
            if id is None:
                self.id = facilityRecordJson['id']
            if name is None:
                self.name = facilityRecordJson['name']
            self.manager_group = GroupModel(groupRecordJson=facilityRecordJson['manager_group'])

    def __str__(self):
        return "FacilityModel " + self.name

    def __unicode__(self):
        return "FacilityModel " + self.name

    def __repr__(self):
        return "FacilityModel " + self.name

    def GetId(self):
        return self.id

    def SetId(self, id):
        self.id = id

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
    def GetFacilityRecord(settingsModel, name):
        myTardisUrl = settingsModel.GetMyTardisUrl()
        myTardisUsername = settingsModel.GetUsername()
        myTardisApiKey = settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/facility/?format=json&name=" + \
            urllib.quote(name)
        headers = {'Authorization': 'ApiKey ' + myTardisUsername + ":" +
                   myTardisApiKey}
        response = requests.get(url=url, headers=headers)
        if response.status_code != 200:
            logger.debug("Failed to look up facility record for name \"" +
                         name + "\".")
            logger.debug(response.text)
            return None
        facilityRecordsJson = response.json()
        numFacilityRecordsFound = facilityRecordsJson['meta']['total_count']

        if numFacilityRecordsFound == 0:
            logger.warning("Facility \"%s\" was not found in MyTardis" % name)
            return None
        else:
            logger.debug("Found facility record for name '" + name + "'.")
            return FacilityModel(settingsModel=settingsModel, name=name,
                             facilityRecordJson=facilityRecordsJson['objects'][0])

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
            response = requests.get(url=url, headers=headers)
            if response.status_code != 200:
                logger.debug("Failed to look up facility record for group \"" +
                             group.GetName() + "\".")
                logger.debug(response.text)
                return None
            facilityRecordsJson = response.json()
            for facilityRecordJson in facilityRecordsJson['objects']:
                facilities.append(FacilityModel(
                    settingsModel=settingsModel,
                    facilityRecordJson=facilityRecordJson))

        return facilities

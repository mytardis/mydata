"""
Model class for MyTardis API v1's FacilityResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import urllib
import requests

from mydata.logs import logger
from mydata.utils.exceptions import DoesNotExist
from .group import GroupModel


class FacilityModel(object):
    """
    Model class for MyTardis API v1's FacilityResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    def __init__(self, settingsModel=None, name=None, facilityJson=None):

        self.settingsModel = settingsModel
        self.facilityId = None
        self.name = name
        self.json = facilityJson
        self.managerGroup = None

        if facilityJson is not None:
            self.facilityId = facilityJson['id']
            if name is None:
                self.name = facilityJson['name']
            self.managerGroup = \
                GroupModel(groupJson=facilityJson['manager_group'])

    def __str__(self):
        return "FacilityModel " + self.name

    def __repr__(self):
        return "FacilityModel " + self.name

    def GetId(self):
        """
        Return the facility ID.
        """
        return self.facilityId

    def GetName(self):
        """
        Return the facility name.
        """
        return self.name

    def GetManagerGroup(self):
        """
        Return the facility managers group.
        """
        return self.managerGroup

    def GetResourceUri(self):
        """
        Return the API resource URI.
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
    def GetFacility(settingsModel, name):
        """
        Get facility by name.
        """
        myTardisUrl = settingsModel.GetMyTardisUrl()

        url = myTardisUrl + "/api/v1/facility/?format=json&name=" + \
            urllib.quote(name.encode('utf-8'))
        response = requests.get(url=url,
                                headers=settingsModel.GetDefaultHeaders())
        logger.debug(response.text)
        if response.status_code != 200:
            message = response.text
            response.close()
            raise Exception(message)
        facilitiesJson = response.json()
        response.close()
        numFacilitiesFound = facilitiesJson['meta']['total_count']

        if numFacilitiesFound == 0:
            message = "Facility \"%s\" was not found in MyTardis" % name
            logger.warning(message)
            raise DoesNotExist(message, response, modelClass=FacilityModel)
        else:
            logger.debug("Found facility record for name '" + name + "'.")
            return FacilityModel(
                settingsModel=settingsModel, name=name,
                facilityJson=facilitiesJson['objects'][0])

    @staticmethod
    def GetMyFacilities(settingsModel):
        """
        Get facilities I have access to (by
        facility managers group membership).
        """
        myTardisUrl = settingsModel.GetMyTardisUrl()

        facilities = []

        url = myTardisUrl + "/api/v1/facility/?format=json"
        response = requests.get(url=url,
                                headers=settingsModel.GetDefaultHeaders())
        if response.status_code != 200:
            message = response.text
            response.close()
            raise Exception(message)
        response.close()
        facilitiesJson = response.json()
        for facilityJson in facilitiesJson['objects']:
            facilities.append(FacilityModel(
                settingsModel=settingsModel,
                facilityJson=facilityJson))

        return facilities

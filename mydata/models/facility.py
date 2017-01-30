"""
Model class for MyTardis API v1's FacilityResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import requests

from .group import GroupModel
from . import HandleHttpError

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
            HandleHttpError(response)
        facilitiesJson = response.json()
        for facilityJson in facilitiesJson['objects']:
            facilities.append(FacilityModel(
                settingsModel=settingsModel,
                facilityJson=facilityJson))
        return facilities

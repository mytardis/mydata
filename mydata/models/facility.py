"""
Model class for MyTardis API v1's FacilityResource.
See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
"""

import requests

from ..settings import SETTINGS
from .group import GroupModel
from . import HandleHttpError


class FacilityModel(object):
    """
    Model class for MyTardis API v1's FacilityResource.
    See: https://github.com/mytardis/mytardis/blob/3.7/tardis/tardis_portal/api.py
    """
    def __init__(self, name=None, facilityJson=None):
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

    @property
    def resourceUri(self):
        """
        Return the API resource URI.
        """
        return self.json['resource_uri']

    @staticmethod
    def GetMyFacilities():
        """
        Get facilities I have access to (by
        facility managers group membership).
        """
        facilities = []
        url = "%s/api/v1/facility/?format=json" % SETTINGS.general.myTardisUrl
        response = requests.get(url=url, headers=SETTINGS.defaultHeaders)
        if response.status_code != 200:
            HandleHttpError(response)
        facilitiesJson = response.json()
        for facilityJson in facilitiesJson['objects']:
            facilities.append(FacilityModel(facilityJson=facilityJson))
        return facilities

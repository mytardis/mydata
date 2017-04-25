"""
The MyDataVersions class contains methods to determine whether we are running
the latest official version, an older version, or a newer version.
"""
from datetime import datetime
import json
import os

import dateutil.parser
import pytz
import requests

from ..models import HandleHttpError
from ..settings import SETTINGS

from ..logs import logger

GITHUB_API_BASE_URL = "https://api.github.com/repos/mytardis/mydata"
CACHE_REFRESH_INTERVAL = 300  # seconds


class MyDataVersions(object):
    """
    The MyDataVersions class contains methods to determine whether we are
    running the latest official version, an older version, or a newer
    version.

    The GitHub API will throttle more than 60 connections per hour from the
    same IP address which I can easily reach while testing MyData, so we cache
    results from GitHub API queries.
    """
    def __init__(self):
        self._latestOfficialRelease = None

    @property
    def latestOfficialRelease(self):
        """
        Gets the latest official release from the GitHub API.
        """
        if self._latestOfficialRelease:
            return self._latestOfficialRelease
        interval = datetime.utcnow().replace(tzinfo=pytz.utc) - \
            self.latestVersionCacheTime
        if interval.total_seconds() > CACHE_REFRESH_INTERVAL:
            url = "%s/releases/latest" % GITHUB_API_BASE_URL
            logger.debug(url)
            response = requests.get(url)
            if response.status_code != 200:
                HandleHttpError(response)
            self._latestOfficialRelease = response.json()
            with open(self.latestVersionCachePath, 'w') as cache:
                cache.write(response.text)
        else:
            with open(self.latestVersionCachePath, 'r') as cache:
                self._latestOfficialRelease = json.load(cache)
        return self._latestOfficialRelease

    @property
    def latestOfficialReleaseDateTime(self):
        """
        Returns the date and time (UTC) of the latest official release.
        """
        return dateutil.parser.parse(
            self.latestOfficialRelease['published_at'])

    @property
    def latestVersionCachePath(self):
        """
        Response from
        https://api.github.com/repos/mytardis/mydata/releases/latest
        is cached to avoid throttling (only 60 requests are allowed
        per hour from the same IP address).  Throttling is unlikely
        to be an issue in production, but in development, running MyData
        more than 60 times within an hour is common.
        """
        assert SETTINGS.configPath
        return os.path.join(
            os.path.dirname(SETTINGS.configPath), "latest-version.json")

    @property
    def latestVersionCacheTime(self):
        """
        Return time when the latest version cache was last updated.
        """
        try:
            return datetime.utcfromtimestamp(
                os.path.getmtime(self.latestVersionCachePath)) \
                .replace(tzinfo=pytz.utc)
        except (OSError, IOError):
            return datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)


MYDATA_VERSIONS = MyDataVersions()

"""
Methods for managing application updates.
"""
import sys
import threading
import traceback

import dateutil.parser
import requests
import wx

from ..utils.versions import MYDATA_VERSIONS
from ..logs import logger
from .. import LATEST_COMMIT_DATETIME
from ..views.update import NewVersionAlertDialog


def VersionCheck():
    """
    Check if we are running the latest version.
    """

    def VersionCheckWorker():
        """
        Check if we are running the latest version.
        """
        if hasattr(sys, "frozen"):
            from .. import __version__ as VERSION
        else:
            from .. import LATEST_COMMIT as VERSION
        latestOfficialReleaseTag = MYDATA_VERSIONS.latestOfficialReleaseTagName
        latestReleaseTag = MYDATA_VERSIONS.latestReleaseTagName
        try:

            if VERSION == MYDATA_VERSIONS.latestOfficialReleaseCommitHash or \
                    "v%s" % VERSION == latestOfficialReleaseTag:
                logger.info(
                    "The version you are running (%s) is the latest "
                    "official release." % VERSION)
                return
            elif VERSION == MYDATA_VERSIONS.latestReleaseCommitHash or \
                    "v%s" % VERSION == latestReleaseTag:
                logger.info(
                    "The version you are running (%s) is the latest "
                    "release." % VERSION)
                return
            currentCommitDateTime = \
                dateutil.parser.parse(LATEST_COMMIT_DATETIME)
            if currentCommitDateTime < \
                    MYDATA_VERSIONS.latestOfficialReleaseDateTime:
                # Latest official release is newer or equal to current version:
                latest = MYDATA_VERSIONS.latestOfficialReleaseTagName
                changes = MYDATA_VERSIONS.latestOfficialReleaseBody
                latestTime = MYDATA_VERSIONS.latestOfficialReleaseDateTime
                releaseType = "official release"
            else:
                # Current version is newer than latest official release,
                # but there might be a newer pre-release version available:
                latest = MYDATA_VERSIONS.latestReleaseTagName
                changes = MYDATA_VERSIONS.latestReleaseBody
                latestTime = MYDATA_VERSIONS.latestReleaseDateTime
                if MYDATA_VERSIONS.latestReleaseIsPreRelease:
                    releaseType = "pre-release version"
                else:
                    releaseType = "official release"
            if currentCommitDateTime < latestTime:
                logger.warning(
                    "The version you are running (%s) is older than the "
                    "latest %s (%s)." % (VERSION, releaseType, latest))

                def ShowUpdateDialog():
                    """
                    Show new version alert dialog
                    """
                    dlg = NewVersionAlertDialog(
                        None, "New MyData Version Available", latest, changes)
                    dlg.ShowModal()
                wx.CallAfter(ShowUpdateDialog)
            else:
                logger.info(
                    "The version you are running (%s) is newer than the "
                    "latest %s (%s)." % (VERSION, releaseType, latest))
        except requests.exceptions.RequestException as err:
            logger.warning(err)
        except:
            logger.warning(traceback.format_exc())

    threading.Thread(target=VersionCheckWorker, name="VersionCheck").start()

"""
Methods for managing application updates.
"""
import threading
import traceback

import dateutil.parser
import requests

from ..utils.versions import MYDATA_VERSIONS
from ..logs import logger
from .. import LATEST_COMMIT_DATETIME


def VersionCheck():
    """
    Check if we are running the latest version.
    """

    def VersionCheckWorker():
        """
        Check if we are running the latest version.
        """
        currentCommitDateTime = dateutil.parser.parse(LATEST_COMMIT_DATETIME)
        try:
            if currentCommitDateTime < \
                    MYDATA_VERSIONS.latestOfficialReleaseDateTime:
                logger.warning(
                    "The version you are running is older than the "
                    "latest official release.")
            elif currentCommitDateTime == \
                    MYDATA_VERSIONS.latestOfficialReleaseDateTime:
                logger.info(
                    "The version you are running is the latest "
                    "official release.")
            else:
                logger.info(
                    "The version you are running is newer than the latest "
                    "official release.")
        except requests.exceptions.RequestException as err:
            logger.warning(err)
        except:
            logger.warning(traceback.format_exc())

    threading.Thread(target=VersionCheckWorker, name="VersionCheck").start()

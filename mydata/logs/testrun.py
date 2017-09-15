"""
Logging methods related to MyData's Test Run
"""
from . import logger
from ..dataviewmodels.dataview import DATAVIEW_MODELS


def LogTestRunSummary():
    """
    Log summary of test run to display in Test Run frame
    """
    numVerificationsCompleted = \
        DATAVIEW_MODELS['verifications'].GetCompletedCount()
    numVerifiedUploads = \
        DATAVIEW_MODELS['verifications'].GetFoundVerifiedCount()
    numFilesNotFoundOnServer = \
        DATAVIEW_MODELS['verifications'].GetNotFoundCount()
    numFullSizeUnverifiedUploads = \
        DATAVIEW_MODELS['verifications'].GetFoundUnverifiedFullSizeCount()
    numIncompleteUploads = \
        DATAVIEW_MODELS['verifications'].GetFoundUnverifiedNotFullSizeCount()
    numFailedLookups = DATAVIEW_MODELS['verifications'].GetFailedCount()
    logger.testrun("")
    logger.testrun("SUMMARY")
    logger.testrun("")
    logger.testrun("Files looked up on server: %s"
                   % numVerificationsCompleted)
    logger.testrun("Files verified on server: %s" % numVerifiedUploads)
    logger.testrun("Files not found on server: %s"
                   % numFilesNotFoundOnServer)
    logger.testrun("Files unverified (but full size) on server: %s"
                   % numFullSizeUnverifiedUploads)
    logger.testrun("Files unverified (and incomplete) on server: %s"
                   % numIncompleteUploads)
    logger.testrun("Failed lookups: %s" % numFailedLookups)
    logger.testrun("")

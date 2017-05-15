"""
Thread-safe flags
"""
import threading


class ThreadSafeFlags(object):
    """
    Thread-safe flags
    """
    def __init__(self):
        self._scanningFolders = threading.Event()
        self._performingLookupsAndUploads = threading.Event()
        self._testRunRunning = threading.Event()
        self._shouldAbort = threading.Event()
        self._isShowingErrorDialog = threading.Event()

    @property
    def scanningFolders(self):
        """
        Returns True if MyData is currently scanning data folders.
        """
        return self._scanningFolders.isSet()

    @scanningFolders.setter
    def scanningFolders(self, value):
        """
        Records whether MyData is currently scanning data folders.
        """
        if value:
            self._scanningFolders.set()
        else:
            self._scanningFolders.clear()

    @property
    def performingLookupsAndUploads(self):
        """
        Returns True if MyData is currently performing
        datafile lookups (verifications) and uploading
        datafiles.
        """
        return self._performingLookupsAndUploads.isSet()

    @performingLookupsAndUploads.setter
    def performingLookupsAndUploads(self, value):
        """
        Records whether MyData is currently performing
        datafile lookups (verifications) and uploading
        datafiles.
        """
        if value:
            self._performingLookupsAndUploads.set()
        else:
            self._performingLookupsAndUploads.clear()

    @property
    def testRunRunning(self):
        """
        Called when the Test Run window is closed to determine
        whether the Test Run is still running.  If so, it will
        be aborted.  If not, we need to be careful to avoid
        aborting a real uploads run.
        """
        return self._testRunRunning.isSet()

    @testRunRunning.setter
    def testRunRunning(self, value):
        """
        Records whether MyData is currently performing a test run.
        """
        if value:
            self._testRunRunning.set()
        else:
            self._testRunRunning.clear()

    @property
    def shouldAbort(self):
        """
        The user has requested aborting the data folder scans and/or
        datafile lookups (verifications) and/or uploads.
        """
        return self._shouldAbort.isSet()

    @shouldAbort.setter
    def shouldAbort(self, shouldAbort):
        """
        The user has requested aborting the data folder scans and/or
        datafile lookups (verifications) and/or uploads.
        """
        if shouldAbort:
            self._shouldAbort.set()
        else:
            self._shouldAbort.clear()

    @property
    def isShowingErrorDialog(self):
        """
        Returns True if an error dialog is currently being displayed.
        """
        return self._isShowingErrorDialog.isSet()

    @isShowingErrorDialog.setter
    def isShowingErrorDialog(self, isShowingErrorDialog):
        """
        Set this to True when displaying an error dialog.
        """
        if isShowingErrorDialog:
            self._isShowingErrorDialog.set()
        else:
            self._isShowingErrorDialog.clear()

FLAGS = ThreadSafeFlags()

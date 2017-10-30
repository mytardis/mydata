"""
Thread-safe flags
"""
import threading


class ThreadSafeFlags(object):
    """
    Thread-safe flags
    """
    def __init__(self):
        self._flags = dict()
        self._flags['scanningFolders'] = threading.Event()
        self._flags['performingLookupsAndUploads'] = threading.Event()
        self._flags['testRunRunning'] = threading.Event()
        self._flags['shouldAbort'] = threading.Event()
        self._flags['showingErrorDialog'] = threading.Event()
        self._flags['showingConfirmationDialog'] = threading.Event()

    @property
    def scanningFolders(self):
        """
        Returns True if MyData is currently scanning data folders.
        """
        return self._flags['scanningFolders'].isSet()

    @scanningFolders.setter
    def scanningFolders(self, value):
        """
        Records whether MyData is currently scanning data folders.
        """
        if value:
            self._flags['scanningFolders'].set()
        else:
            self._flags['scanningFolders'].clear()

    @property
    def performingLookupsAndUploads(self):
        """
        Returns True if MyData is currently performing
        datafile lookups (verifications) and uploading
        datafiles.
        """
        return self._flags['performingLookupsAndUploads'].isSet()

    @performingLookupsAndUploads.setter
    def performingLookupsAndUploads(self, value):
        """
        Records whether MyData is currently performing
        datafile lookups (verifications) and uploading
        datafiles.
        """
        if value:
            self._flags['performingLookupsAndUploads'].set()
        else:
            self._flags['performingLookupsAndUploads'].clear()

    @property
    def testRunRunning(self):
        """
        Called when the Test Run window is closed to determine
        whether the Test Run is still running.  If so, it will
        be aborted.  If not, we need to be careful to avoid
        aborting a real uploads run.
        """
        return self._flags['testRunRunning'].isSet()

    @testRunRunning.setter
    def testRunRunning(self, value):
        """
        Records whether MyData is currently performing a test run.
        """
        if value:
            self._flags['testRunRunning'].set()
        else:
            self._flags['testRunRunning'].clear()

    @property
    def shouldAbort(self):
        """
        The most common reason for setting "shouldAbort" to True is when the
        user has requested aborting the data folder scans and/or datafile
        lookups (verifications) and/or uploads.

        It is also set when a critical failure / unhandled exception means
        that MyData needs to shut down the uploads before completion.

        When FoldersController's ShutDownUploadThreads finishes running, it
        will restore FLAGS.shouldAbort to its default value of False, but
        foldersController.canceled will remain set to True if the last session
        was canceled.  foldersController.canceled will be reset in
        FoldersController's InitializeStatusFlags method the next time we run
        the scans and uploads.
        """
        return self._flags['shouldAbort'].isSet()

    @shouldAbort.setter
    def shouldAbort(self, shouldAbort):
        """
        The user has requested aborting the data folder scans and/or
        datafile lookups (verifications) and/or uploads.
        """
        if shouldAbort:
            self._flags['shouldAbort'].set()
        else:
            self._flags['shouldAbort'].clear()

    @property
    def showingErrorDialog(self):
        """
        Returns True if an error dialog is currently being displayed.
        """
        return self._flags['showingErrorDialog'].isSet()

    @showingErrorDialog.setter
    def showingErrorDialog(self, showingErrorDialog):
        """
        Set this to True when displaying an error dialog.
        """
        if showingErrorDialog:
            self._flags['showingErrorDialog'].set()
        else:
            self._flags['showingErrorDialog'].clear()

    @property
    def showingConfirmationDialog(self):
        """
        Returns True if a confirmation dialog is currently being displayed.
        """
        return self._flags['showingConfirmationDialog'].isSet()

    @showingConfirmationDialog.setter
    def showingConfirmationDialog(self, showingConfirmationDialog):
        """
        Set this to True when displaying a confirmation dialog.
        """
        if showingConfirmationDialog:
            self._flags['showingConfirmationDialog'].set()
        else:
            self._flags['showingConfirmationDialog'].clear()

FLAGS = ThreadSafeFlags()

"""
Locks for thread synchronization
"""
import threading


class ThreadingLocks(object):
    """
    Locks for thread synchronization
    """
    def __init__(self):
        self.scanningFoldersThreadingLock = threading.Lock()

        self.createUploaderThreadingLock = threading.Lock()
        self.requestStagingAccessThreadLock = threading.Lock()

        # Verified datafiles cache:
        self.initializeCacheLock = threading.Lock()
        self.updateCacheLock = threading.Lock()
        self.closeCacheLock = threading.Lock()

        # Display modal dialog lock:
        self.displayModalDialog = threading.Lock()

        # Update last error message lock:
        self.updateLastErrorMessage = threading.Lock()

        # Update last confirmation question lock:
        self.updateLastConfirmationQuestion = threading.Lock()

LOCKS = ThreadingLocks()

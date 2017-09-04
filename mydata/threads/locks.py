"""
Locks for thread synchronization
"""
import threading

LOCK_NAMES = [
    'scanningFolders', 'createUploader', 'requestStagingAccess',
    'updateCache', 'closeCache', 'displayModalDialog',
    'updateLastErrorMessage', 'updateLastConfirmationQuestion',
    'addVerification', 'addUpload', 'finishedCounting', 'getOrCreateExp',
    'numVerificationsToBePerformed', 'createDir']

class ThreadingLocks(object):
    """
    Locks for thread synchronization.

    Each lock can be accessed as LOCKS.[lockName] e.g. LOCKS.updateCache
    where LOCKS is the singleton instance of the ThreadingLocks class.

    Usage:

        from .threads.locks import LOCKS
        with LOCKS.updateCache:
            UpdateCache()
    """
    def __init__(self):
        """
        We will only define one instance of the ThreadingLocks class,
        called 'LOCKS', so the 'self' in the lambda expression will
        always be the LOCKS instance.
        """
        self._locks = dict()
        for lockName in LOCK_NAMES:
            self._locks[lockName] = threading.Lock()
            setattr(ThreadingLocks, lockName,
                    property(lambda self, key=lockName: self._locks[key]))


LOCKS = ThreadingLocks()

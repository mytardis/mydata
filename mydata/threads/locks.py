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

LOCKS = ThreadingLocks()

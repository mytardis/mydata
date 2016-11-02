"""
On Linux, running subprocess the usual way can be inefficient, due to
its use of os.fork.  So on Linux, we can use errand_boy to run our
subprocesses for us.
"""
import multiprocessing
import time

# pylint: disable=import-error
from errand_boy.transports.unixsocket import UNIXSocketTransport

ERRAND_BOY_PROCESS = None
ERRAND_BOY_TRANSPORT = None

ERRAND_BOY_NUM_WORKERS = 10
ERRAND_BOY_MAX_ACCEPTS = 5000
ERRAND_BOY_MAX_CHILD_TASKS = 100

def StartErrandBoy():
    """
    Start errand boy.
    """
    if not ERRAND_BOY_TRANSPORT:
        globals()['ERRAND_BOY_TRANSPORT'] = UNIXSocketTransport()
    def RunErrandBoyServer():
        """
        Run the errand boy server.
        """
        ERRAND_BOY_TRANSPORT.run_server(
            pool_size=ERRAND_BOY_NUM_WORKERS,
            max_accepts=ERRAND_BOY_MAX_ACCEPTS,
            max_child_tasks=ERRAND_BOY_MAX_CHILD_TASKS
        )
    globals()['ERRAND_BOY_PROCESS'] = \
        multiprocessing.Process(target=RunErrandBoyServer)
    ERRAND_BOY_PROCESS.start()

def StopErrandBoy():
    """
    Stop errand boy.
    """
    if ERRAND_BOY_PROCESS:
        ERRAND_BOY_PROCESS.terminate()

def GetErrandBoyTransport():
    """
    Return the errand boy transport, creating it if necessary.
    """
    if not ERRAND_BOY_TRANSPORT:
        globals()['ERRAND_BOY_TRANSPORT'] = UNIXSocketTransport()
    if not ERRAND_BOY_PROCESS:
        StartErrandBoy()
        started = False
        count = 0
        while not started and count < 10:
            time.sleep(0.1)
            try:
                ERRAND_BOY_TRANSPORT.run_cmd('test TRUE')
                break
            except IOError:
                pass
    return ERRAND_BOY_TRANSPORT

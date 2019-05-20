"""
Custom events for MyData.
"""
import logging
import wx

from ..views.messages import ShowMessageDialog
from ..logs import logger

from .handlers import ShutdownForRefresh
from .handlers import ShutdownForRefreshComplete
from .handlers import ValidateSettingsForRefresh
from .handlers import CheckConnectivity
from .handlers import InstrumentNameMismatch
from .handlers import RenameInstrument
from .handlers import SettingsDialogValidation
from .handlers import ProvideSettingsValidationResults
from .handlers import SettingsValidationForRefreshComplete
from .handlers import StartDataUploadsForFolder
from .handlers import DidntFindDatafileOnServer
from .handlers import FoundIncompleteStaged
from .handlers import FoundVerifiedDatafile
from .handlers import FoundFullSizeStaged
from .handlers import FoundUnverifiedNoDfosDatafile
from .handlers import FoundUnverifiedUnstaged
from .handlers import UploadComplete
from .handlers import UploadFailed
from .handlers import ShutDownUploads


def NewEvent(defaultTarget=None, defaultHandler=None):
    """
    Generate new (Event, eventType) tuple
        e.g. MooEvent, EVT_MOO = NewEvent()
    """
    eventType = wx.NewEventType()

    class Event(wx.PyEvent):
        """ Custom event class """
        defaultEventTarget = defaultTarget
        defaultEventHandler = defaultHandler

        @staticmethod
        def GetDefaultTarget():
            """ Return default target. """
            return Event.defaultEventTarget

        @staticmethod
        def GetDefaultHandler():
            """ Return default handler. """
            return Event.defaultEventHandler

        def __init__(self, **kw):
            wx.PyEvent.__init__(self)
            self.SetEventType(eventType)
            if 'phoenix' in wx.PlatformInfo:
                self._getAttrDict().update(kw)
            else:
                self.__dict__.update(kw)

    eventBinder = wx.PyEventBinder(eventType)

    if defaultTarget and defaultHandler:
        defaultTarget.Bind(eventBinder, defaultHandler)

    return Event, eventType


def PostEvent(event):
    """
    For now, just call wx.PostEvent, but later this will be able to call the
    event's default handler directly if necessary, eliminating the dependency
    on wxPython's event loop.  This is useful for automated testing.
    """
    # pylint: disable=too-many-branches
    app = wx.GetApp()
    eventTypeId = event.GetEventType()
    eventTypeString = None
    if logger.GetLevel() == logging.DEBUG:
        keys = dir(MYDATA_EVENTS)
        for key in keys:
            if key.startswith("EVT_") and \
                    getattr(MYDATA_EVENTS, key) == eventTypeId:
                eventTypeString = key
                logger.debug("Posting %s" % eventTypeString)
    if wx.PyApp.IsMainLoopRunning():
        target = event.GetDefaultTarget()
        if not target:
            target = app.frame
        wx.PostEvent(target, event)
    else:
        if hasattr(event, "GetDefaultHandler"):
            if not eventTypeString:
                eventTypeString = str(eventTypeId)
            logger.debug("Calling default handler for %s" % eventTypeString)
            event.GetDefaultHandler()(event)
            logger.debug("Called default handler for %s" % eventTypeString)
        else:
            logger.debug("Didn't find default handler for %s"
                         % eventTypeString)


# List of tuples, each with
# the event class name, the event type name, and the event handler:
_EVENT_TUPLES = [
    ('ShutdownForRefreshEvent', 'EVT_SHUTDOWN_FOR_REFRESH',
     ShutdownForRefresh),
    ('ShutdownForRefreshCompleteEvent', 'EVT_SHUTDOWN_FOR_REFRESH_COMPLETE',
     ShutdownForRefreshComplete),
    ('ValidateSettingsForRefreshEvent', 'EVT_VALIDATE_SETTINGS_FOR_REFRESH',
     ValidateSettingsForRefresh),
    ('CheckConnectivityEvent', 'EVT_CHECK_CONNECTIVITY', CheckConnectivity),
    ('InstrumentNameMismatchEvent', 'EVT_INSTRUMENT_NAME_MISMATCH',
     InstrumentNameMismatch),
    ('RenameInstrumentEvent', 'EVT_RENAME_INSTRUMENT', RenameInstrument),
    ('SettingsDialogValidationEvent', 'EVT_SETTINGS_DIALOG_VALIDATION',
     SettingsDialogValidation),
    ('ProvideSettingsValidationResultsEvent', 'EVT_PROVIDE_SETTINGS_VALIDATION_RESULTS',
     ProvideSettingsValidationResults),
    ('SettingsValidationCompleteEvent', 'EVT_SETTINGS_VALIDATION_COMPLETE',
     SettingsValidationForRefreshComplete),
    ('StartUploadsForFolderEvent', 'EVT_START_UPLOADS_FOR_FOLDER',
     StartDataUploadsForFolder),
    ('ShowMessageDialogEvent', 'EVT_SHOW_MESSAGE_DIALOG', ShowMessageDialog),
    ('DidntFindDatafileOnServerEvent', 'EVT_DIDNT_FIND_FILE_ON_SERVER',
     DidntFindDatafileOnServer),
    ('FoundIncompleteStagedEvent', 'EVT_FOUND_INCOMPLETE_STAGED',
     FoundIncompleteStaged),
    ('FoundVerifiedDatafileEvent', 'EVT_FOUND_VERIFIED',
     FoundVerifiedDatafile),
    ('FoundFullSizeStagedEvent', 'EVT_FOUND_FULLSIZE_STAGED',
     FoundFullSizeStaged),
    ('FoundUnverifiedNoDfosDatafileEvent', 'EVT_FOUND_UNVERIFIED_NO_DFOS',
     FoundUnverifiedNoDfosDatafile),
    ('FoundUnverifiedUnstagedEvent', 'EVT_FOUND_UNVERIFIED_UNSTAGED',
     FoundUnverifiedUnstaged),
    ('UploadCompleteEvent', 'EVT_UPLOAD_COMPLETE', UploadComplete),
    ('UploadFailedEvent', 'EVT_UPLOAD_FAILED', UploadFailed),
    ('ShutdownUploadsEvent', 'EVT_SHUTDOWN_UPLOADS', ShutDownUploads)]


class MyDataEvents(object):
    """
    Custom events for MyData.

    The event types (EVT_...) are used for logging in the PostEvent method.

    Each event class can be accessed as MYDATA_EVENTS.[EventClassName]
    e.g. MYDATA_EVENTS.StartUploadsForFolderEvent
    where MYDATA_EVENTS is the singleton instance of the MyDataEvents class.

    """
    def __init__(self):
        self.notifyWindow = None
        self._eventClasses = dict()
        self._eventTypes = dict()

    def InitializeWithNotifyWindow(self, notifyWindow):
        """
        Set notify window (main frame), and create event classes using the
        NewEvent function above which automatically binds events to their
        default handler.
        """
        self.notifyWindow = notifyWindow
        for eventClass, eventType, eventHandler in _EVENT_TUPLES:
            evtClass, evtType = NewEvent(notifyWindow, eventHandler)
            self._eventClasses[eventClass] = evtClass
            setattr(
                MyDataEvents, eventClass,
                property(lambda self, key=eventClass: self._eventClasses[key]))
            self._eventTypes[eventType] = evtType
            setattr(
                MyDataEvents, eventType,
                property(lambda self, key=eventType: self._eventTypes[key]))

    def GetNotifyWindow(self):
        """
        Returns the wx.Frame which propagates events,
        which is MyData's main frame..
        """
        return self.notifyWindow


MYDATA_EVENTS = MyDataEvents()


class MyDataThreads(object):
    """
    Thread pool for MyData.
    """
    def __init__(self):
        self.threads = []

    def __str__(self):
        return str(self.threads)

    def Add(self, thread):
        """
        Register additional thread.
        """
        self.threads.append(thread)

    def Join(self):
        """
        Join threads.
        """
        for thread in self.threads:
            thread.join()
            logger.debug("\tJoined %s" % thread.name)


MYDATA_THREADS = MyDataThreads()

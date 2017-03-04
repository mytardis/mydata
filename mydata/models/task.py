"""
Model for representing a scheduled task (a.k.a. job), as listed
in the Tasks view of MyData's main window.
"""


class DayOfWeek(object):
    """
    Enumerated data type.
    """
    MON = 0
    TUE = 1
    WED = 2
    THU = 3
    FRI = 4
    SAT = 5
    SUN = 6


class TaskModel(object):
    """
    Model for reprenting a scheduled task (a.k.a. job), as listed
    in the Tasks view of MyData's main window.

    A task can be a folder scan, datafile lookup and upload,
    or it could be a notification POSTed to MyTardis administrators.
    """
    def __init__(self, dataViewId, jobFunc, jobArgs, jobDesc, startTime,
                 scheduleType="Once", intervalMinutes=None, days=None):
        self.dataViewId = dataViewId
        self.jobFunc = jobFunc
        self.jobArgs = jobArgs
        self.jobDesc = jobDesc
        self.startTime = startTime
        self.finishTime = None
        self.scheduleType = scheduleType
        self.intervalMinutes = intervalMinutes
        self.days = days
        self.callLater = None

    def Cancel(self):
        """
        Cancel the task
        """
        if self.callLater:
            self.callLater.Stop()

    def GetValueForKey(self, key):
        """
        Used in the data view model to look up a value from a column key
        """
        return self.__dict__[key]

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
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=missing-docstring
    def __init__(self, dataViewId, jobFunc, jobArgs, jobDesc, startTime,
                 scheduleType="Once", intervalMinutes=None, days=None):
        # pylint: disable=too-many-arguments
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

    def GetDataViewId(self):
        return self.dataViewId

    def GetJobFunc(self):
        return self.jobFunc

    def GetJobArgs(self):
        return self.jobArgs

    def GetJobDesc(self):
        return self.jobDesc

    def GetStartTime(self):
        return self.startTime

    def GetScheduleType(self):
        return self.scheduleType

    def GetIntervalMinutes(self):
        return self.intervalMinutes

    def GetDays(self):
        return self.days

    def GetFinishTime(self):
        return self.finishTime

    def SetFinishTime(self, finishTime):
        self.finishTime = finishTime

    def GetCallLater(self):
        return self.callLater

    def SetCallLater(self, callLater):
        self.callLater = callLater

    def Cancel(self):
        if self.callLater:
            self.callLater.Stop()

    def GetValueForKey(self, key):
        return self.__dict__[key]

"""
Represents the Tasks tab of MyData's main window,
and the tabular data displayed on that tab view.
"""
import sys
import threading
from datetime import datetime
from datetime import timedelta

import wx

from ..events.stop import CheckIfShouldAbort
from ..models.task import TaskModel
from ..utils.notification import Notification
from ..logs import logger
from .dataview import MyDataDataViewModel


class TasksModel(MyDataDataViewModel):
    """
    Represents the Tasks tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-many-public-methods
    # pylint: disable=arguments-differ
    def __init__(self):
        super(TasksModel, self).__init__()
        self.columnNames = ["Id", "Job", "Start Time", "Finish Time",
                            "Schedule Type", "Interval (minutes)"]
        self.columnKeys = ["dataViewId", "jobDesc", "startTime", "finishTime",
                           "scheduleType", "intervalMinutes"]
        self.defaultColumnWidths = [40, 300, 200, 200, 115, 100]

    def GetValueByRow(self, row, col):
        """
        This method is called to provide the rowsData object
        for a particular row, col
        """
        columnKey = self.GetColumnKeyName(col)
        value = self.rowsData[row].GetValueForKey(columnKey)
        if value is None:
            return ""
        elif columnKey in ("startTime", "finishTime"):
            timeString = value.strftime("%I:%M:%S %p")
            dateString = "{d:%a} {d.day}/{d.month}/{d.year}".format(d=value)
            return value.strftime("%s on %s" % (timeString, dateString))
        elif columnKey == "scheduleType" and value == "Weekly":
            value += " ("
            days = self.rowsData[row].days
            value += 'M' if days[0] else '-'
            value += 'T' if days[1] else '-'
            value += 'W' if days[2] else '-'
            value += 'T' if days[3] else '-'
            value += 'F' if days[4] else '-'
            value += 'S' if days[5] else '-'
            value += 'S' if days[6] else '-'
            value += ")"
        return str(value)

    def AddRow(self, taskModel):
        """
        Add a task to the Tasks view and activate it.
        """
        super(TasksModel, self).AddRow(taskModel)

        def JobFunc(taskModel, row, col):
            """
            Runs TaskJobFunc in a thread.
            """
            # pylint: disable=too-many-statements
            tasksModel = self

            def TaskJobFunc():
                """
                Runs taskModel.jobFunc and schedules the task to repeat
                according to the schedule type.
                """
                assert callable(taskModel.jobFunc)
                title = "Starting"
                message = taskModel.jobDesc
                Notification.Notify(message, title=title)
                taskModel.jobFunc(*taskModel.jobArgs)
                taskModel.finishTime = datetime.now()
                title = "Finished"
                message = taskModel.jobDesc
                Notification.Notify(message, title=title)
                if wx.PyApp.IsMainLoopRunning():
                    wx.CallAfter(tasksModel.TryRowValueChanged, row, col)
                else:
                    tasksModel.TryRowValueChanged(row, col)
                if taskModel.scheduleType == "Timer":
                    newTaskDataViewId = tasksModel.GetMaxDataViewId() + 1
                    newStartTime = taskModel.startTime + \
                        timedelta(minutes=taskModel.intervalMinutes)
                    newTaskModel = TaskModel(
                        newTaskDataViewId, taskModel.jobFunc,
                        taskModel.jobArgs, taskModel.jobDesc,
                        newStartTime, scheduleType="Timer",
                        intervalMinutes=taskModel.intervalMinutes)
                    timeString = newStartTime.strftime("%I:%M:%S %p")
                    dateString = "{d:%A} {d.day}/{d.month}/{d.year}"\
                        .format(d=newStartTime)
                    msg = ("The \"%s\" task is scheduled "
                           "to run at %s on %s "
                           "(recurring every %d minutes)"
                           % (taskModel.jobDesc,
                              timeString, dateString, taskModel.intervalMinutes))
                    if wx.PyApp.IsMainLoopRunning():
                        wx.CallAfter(wx.GetApp().frame.SetStatusMessage, msg)
                        tasksModel.AddRow(newTaskModel)
                    else:
                        sys.stderr.write("%s\n" % msg)
                elif taskModel.scheduleType == "Daily":
                    newTaskDataViewId = tasksModel.GetMaxDataViewId() + 1
                    newStartTime = taskModel.startTime + timedelta(days=1)
                    newTaskModel = TaskModel(newTaskDataViewId,
                                             taskModel.jobFunc,
                                             taskModel.jobArgs,
                                             taskModel.jobDesc,
                                             newStartTime,
                                             scheduleType="Daily")
                    timeString = newStartTime.strftime("%I:%M:%S %p")
                    dateString = "{d:%A} {d.day}/{d.month}/{d.year}"\
                        .format(d=newStartTime)
                    msg = ("The \"%s\" task is scheduled "
                           "to run at %s on %s "
                           "(recurring daily)"
                           % (taskModel.jobDesc,
                              timeString, dateString))
                    if wx.PyApp.IsMainLoopRunning():
                        wx.CallAfter(wx.GetApp().frame.SetStatusMessage, msg)
                        tasksModel.AddRow(newTaskModel)
                    else:
                        sys.stderr.write("%s\n" % msg)
                elif taskModel.scheduleType == "Weekly":
                    newTaskDataViewId = tasksModel.GetMaxDataViewId() + 1
                    newStartTime = taskModel.startTime + timedelta(days=1)
                    while not taskModel.days[newStartTime.weekday()]:
                        newStartTime = newStartTime + timedelta(days=1)
                    newTaskModel = TaskModel(
                        newTaskDataViewId, taskModel.jobFunc,
                        taskModel.jobArgs, taskModel.jobDesc,
                        newStartTime, scheduleType="Weekly",
                        days=taskModel.days)
                    timeString = newStartTime.strftime("%I:%M:%S %p")
                    dateString = "{d:%A} {d.day}/{d.month}/{d.year}"\
                        .format(d=newStartTime)
                    msg = ("The \"%s\" task is scheduled "
                           "to run at %s on %s "
                           "(recurring on specified days)"
                           % (taskModel.jobDesc,
                              timeString, dateString))
                    if wx.PyApp.IsMainLoopRunning():
                        wx.CallAfter(wx.GetApp().frame.SetStatusMessage, msg)
                        tasksModel.AddRow(newTaskModel)
                    else:
                        sys.stderr.write("%s\n" % msg)

            app = wx.GetApp()
            if not CheckIfShouldAbort() and \
                    not app.foldersController.started:
                if wx.PyApp.IsMainLoopRunning():
                    thread = threading.Thread(target=TaskJobFunc)
                    logger.debug("Starting task %s" % taskModel.jobDesc)
                    thread.start()
                else:
                    TaskJobFunc()
            else:
                if CheckIfShouldAbort():
                    logger.warning(
                        "Not starting task because we are aborting.")
                    message = "Data scans and uploads were canceled."
                    wx.GetApp().frame.SetStatusMessage(message)
                else:
                    logger.warning(
                        "Not starting task because scans and uploads are "
                        "already running.")
                return

        row = len(self.rowsData) - 1
        col = self.columnKeys.index("finishTime")
        delta = taskModel.startTime - datetime.now()
        millis = delta.total_seconds() * 1000
        if millis < 0:
            if millis > -1000:
                millis = 1
            else:
                raise Exception("Scheduled time for task ID %d "
                                "is in the past." % taskModel.dataViewId)
        args = [taskModel, row, col]

        def ScheduleTask():
            """
            Schedule task, using wx.CallLater.
            """
            taskModel.callLater = wx.CallLater(millis, JobFunc, *args)

        if wx.PyApp.IsMainLoopRunning():
            wx.CallAfter(ScheduleTask)
        else:
            JobFunc(*args)

    def ShutDown(self):
        """
        Shut down all tasks.
        """
        for task in self.rowsData:
            task.callLater.Stop()

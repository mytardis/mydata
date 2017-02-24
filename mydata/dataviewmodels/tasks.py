"""
Represents the Tasks tab of MyData's main window,
and the tabular data displayed on that tab view.
"""

# pylint: disable=wrong-import-position

import sys
import threading
import traceback
from datetime import datetime
from datetime import timedelta

import wx
if wx.version().startswith("3.0.3.dev"):
    from wx.dataview import DataViewIndexListModel  # pylint: disable=no-name-in-module
else:
    from wx.dataview import PyDataViewIndexListModel as DataViewIndexListModel

from ..models.task import TaskModel
from ..utils.notification import Notification
from ..logs import logger
from ..utils import EndBusyCursorIfRequired


class TasksModel(DataViewIndexListModel):
    """
    Represents the Tasks tab of MyData's main window,
    and the tabular data displayed on that tab view.
    """
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
    def __init__(self, settingsModel):
        self.settingsModel = settingsModel
        self.tasksData = list()
        DataViewIndexListModel.__init__(self, len(self.tasksData))
        self.columnNames = ("Id", "Job", "Start Time", "Finish Time",
                            "Schedule Type", "Interval (minutes)")
        self.columnKeys = ("dataViewId", "jobDesc", "startTime", "finishTime",
                           "scheduleType", "intervalMinutes")
        self.defaultColumnWidths = (40, 300, 200, 200, 115, 100)

        # This is the largest ID value which has been used in this model.
        # It may no longer exist, i.e. if we delete the row with the
        # largest ID, we don't decrement the maximum ID.
        self.maxDataViewId = 0

    def GetColumnType(self, col):
        """
        All of our columns are strings.  If the model or the renderers
        in the view are other types then that should be reflected here.
        """
        # pylint: disable=arguments-differ
        # pylint: disable=unused-argument
        # pylint: disable=no-self-use
        return "string"

    def GetValueByRow(self, row, col):
        """
        This method is called to provide the tasksData object
        for a particular row, col
        """
        # pylint: disable=arguments-differ
        columnKey = self.GetColumnKeyName(col)
        value = self.tasksData[row].GetValueForKey(columnKey)
        if value is None:
            return ""
        elif columnKey in ("startTime", "finishTime"):
            timeString = value.strftime("%I:%M:%S %p")
            dateString = "{d:%a} {d.day}/{d.month}/{d.year}".format(d=value)
            return value.strftime("%s on %s" % (timeString, dateString))
        elif columnKey == "scheduleType" and value == "Weekly":
            value += " ("
            days = self.tasksData[row].GetDays()
            value += 'M' if days[0] else '-'
            value += 'T' if days[1] else '-'
            value += 'W' if days[2] else '-'
            value += 'T' if days[3] else '-'
            value += 'F' if days[4] else '-'
            value += 'S' if days[5] else '-'
            value += 'S' if days[6] else '-'
            value += ")"
        return str(value)

    def GetColumnName(self, col):
        """
        Get column name.
        """
        # pylint: disable=arguments-differ
        return self.columnNames[col]

    def GetColumnKeyName(self, col):
        """
        Get column key name.
        """
        return self.columnKeys[col]

    def GetDefaultColumnWidth(self, col):
        """
        Get default column width.
        """
        return self.defaultColumnWidths[col]

    def GetRowCount(self):
        """
        Report how many rows this model provides data for.
        """
        # pylint: disable=arguments-differ
        return len(self.tasksData)

    def GetColumnCount(self):
        """
        Report how many columns this model provides data for.
        """
        # pylint: disable=arguments-differ
        return len(self.columnNames)

    def GetCount(self):
        """
        Report the number of rows in the model
        """
        # pylint: disable=arguments-differ
        return len(self.tasksData)

    def GetAttrByRow(self, row, col, attr):
        """
        Called to check if non-standard attributes should be
        used in the cell at (row, col)
        """
        # pylint: disable=unused-argument
        # pylint: disable=arguments-differ
        # pylint: disable=no-self-use
        return False

    def DeleteAllRows(self):
        """
        Delete all rows.
        """
        rowsDeleted = []
        for row in reversed(range(0, self.GetCount())):
            self.tasksData[row].Cancel()
            del self.tasksData[row]
            rowsDeleted.append(row)

        # notify the view(s) using this model that it has been removed
        if threading.current_thread().name == "MainThread":
            self.RowsDeleted(rowsDeleted)
        else:
            wx.CallAfter(self.RowsDeleted, rowsDeleted)

    def GetMaxDataViewIdFromExistingRows(self):
        """
        Get maximum dataview ID from existing rows.
        """
        maxDataViewId = 0
        for row in range(0, self.GetCount()):
            if self.tasksData[row].GetDataViewId() > maxDataViewId:
                maxDataViewId = self.tasksData[row].GetDataViewId()
        return maxDataViewId

    def GetMaxDataViewId(self):
        """
        Get maximum dataview ID.
        """
        if self.GetMaxDataViewIdFromExistingRows() > self.maxDataViewId:
            self.maxDataViewId = self.GetMaxDataViewIdFromExistingRows()
        return self.maxDataViewId

    def TryRowValueChanged(self, row, col):
        """
        Use try/except when calling RowValueChanged, because
        sometimes there are timing issues which raise wx
        assertions suggesting that the row index we are trying
        to report a change on is greater than or equal to the
        total number of rows in the model.
        """
        try:
            if row < self.GetCount():
                self.RowValueChanged(row, col)
            else:
                logger.warning("TryRowValueChanged called with "
                               "row=%d, self.GetRowCount()=%d" %
                               (row, self.GetRowCount()))
                self.RowValueChanged(row, col)
        except wx.PyAssertionError:
            logger.warning(traceback.format_exc())

    def AddRow(self, taskModel):
        """ Add a task to the Tasks view and activate it. """
        self.tasksData.append(taskModel)
        # Ensure that we save the largest ID used so far:
        self.GetMaxDataViewId()
        # Notify views
        if threading.current_thread().name == "MainThread":
            self.RowAppended()
        else:
            wx.CallAfter(self.RowAppended)

        def JobFunc(taskModel, tasksModel, row, col):
            """
            Runs TaskJobFunc in a thread.
            """
            # pylint: disable=too-many-statements

            def TaskJobFunc():
                """
                Runs taskModel.GetJobFunc() and schedules the task to repeat
                according to the schedule type.
                """
                assert callable(taskModel.GetJobFunc())
                title = "Starting"
                message = taskModel.GetJobDesc()
                Notification.Notify(message, title=title)
                taskModel.GetJobFunc()(*taskModel.GetJobArgs())
                taskModel.SetFinishTime(datetime.now())
                title = "Finished"
                message = taskModel.GetJobDesc()
                Notification.Notify(message, title=title)
                if wx.PyApp.IsMainLoopRunning():
                    wx.CallAfter(tasksModel.TryRowValueChanged, row, col)
                else:
                    tasksModel.TryRowValueChanged(row, col)
                scheduleType = taskModel.GetScheduleType()
                if scheduleType == "Timer":
                    intervalMinutes = taskModel.GetIntervalMinutes()
                    newTaskDataViewId = tasksModel.GetMaxDataViewId() + 1
                    newStartTime = taskModel.GetStartTime() + \
                        timedelta(minutes=intervalMinutes)
                    newTaskModel = TaskModel(newTaskDataViewId,
                                             taskModel.GetJobFunc(),
                                             taskModel.GetJobArgs(),
                                             taskModel.GetJobDesc(),
                                             newStartTime,
                                             scheduleType="Timer",
                                             intervalMinutes=intervalMinutes)
                    timeString = newStartTime.strftime("%I:%M:%S %p")
                    dateString = "{d:%A} {d.day}/{d.month}/{d.year}"\
                        .format(d=newStartTime)
                    msg = ("The \"%s\" task is scheduled "
                           "to run at %s on %s "
                           "(recurring every %d minutes)"
                           % (taskModel.GetJobDesc(),
                              timeString, dateString, intervalMinutes))
                    if wx.PyApp.IsMainLoopRunning():
                        wx.CallAfter(wx.GetApp().frame.SetStatusMessage, msg)
                        tasksModel.AddRow(newTaskModel)
                    else:
                        sys.stderr.write("%s\n" % msg)
                elif scheduleType == "Daily":
                    newTaskDataViewId = tasksModel.GetMaxDataViewId() + 1
                    newStartTime = taskModel.GetStartTime() + \
                        timedelta(days=1)
                    newTaskModel = TaskModel(newTaskDataViewId,
                                             taskModel.GetJobFunc(),
                                             taskModel.GetJobArgs(),
                                             taskModel.GetJobDesc(),
                                             newStartTime,
                                             scheduleType="Daily")
                    timeString = newStartTime.strftime("%I:%M:%S %p")
                    dateString = "{d:%A} {d.day}/{d.month}/{d.year}"\
                        .format(d=newStartTime)
                    msg = ("The \"%s\" task is scheduled "
                           "to run at %s on %s "
                           "(recurring daily)"
                           % (taskModel.GetJobDesc(),
                              timeString, dateString))
                    if wx.PyApp.IsMainLoopRunning():
                        wx.CallAfter(wx.GetApp().frame.SetStatusMessage, msg)
                        tasksModel.AddRow(newTaskModel)
                    else:
                        sys.stderr.write("%s\n" % msg)
                elif scheduleType == "Weekly":
                    newTaskDataViewId = tasksModel.GetMaxDataViewId() + 1
                    newStartTime = taskModel.GetStartTime() + \
                        timedelta(days=1)
                    days = taskModel.GetDays()
                    while not days[newStartTime.weekday()]:
                        newStartTime = newStartTime + timedelta(days=1)
                    newTaskModel = TaskModel(newTaskDataViewId,
                                             taskModel.GetJobFunc(),
                                             taskModel.GetJobArgs(),
                                             taskModel.GetJobDesc(),
                                             newStartTime,
                                             scheduleType="Weekly",
                                             days=days)
                    timeString = newStartTime.strftime("%I:%M:%S %p")
                    dateString = "{d:%A} {d.day}/{d.month}/{d.year}"\
                        .format(d=newStartTime)
                    msg = ("The \"%s\" task is scheduled "
                           "to run at %s on %s "
                           "(recurring on specified days)"
                           % (taskModel.GetJobDesc(),
                              timeString, dateString))
                    if wx.PyApp.IsMainLoopRunning():
                        wx.CallAfter(wx.GetApp().frame.SetStatusMessage, msg)
                        tasksModel.AddRow(newTaskModel)
                    else:
                        sys.stderr.write("%s\n" % msg)

            app = wx.GetApp()
            if not app.ShouldAbort():
                if wx.PyApp.IsMainLoopRunning():
                    thread = threading.Thread(target=TaskJobFunc)
                    logger.debug("Starting task %s" % taskModel.GetJobDesc())
                    thread.start()
                else:
                    TaskJobFunc()
            else:
                logger.info("Not starting task because we are aborting.")
                app.EnableTestAndUploadToolbarButtons()
                EndBusyCursorIfRequired()
                app.SetShouldAbort(False)
                message = "Data scans and uploads were canceled."
                wx.GetApp().GetMainFrame().SetStatusMessage(message)
                return

        row = len(self.tasksData) - 1
        col = self.columnKeys.index("finishTime")
        delta = taskModel.GetStartTime() - datetime.now()
        millis = delta.total_seconds() * 1000
        if millis < 0:
            if millis > -1000:
                millis = 1
            else:
                raise Exception("Scheduled time for task ID %d "
                                "is in the past."
                                % taskModel.GetDataViewId())
        args = [taskModel, self, row, col]

        def ScheduleTask():
            """
            Schedule task, using wx.CallLater.
            """
            callLater = wx.CallLater(millis, JobFunc, *args)
            taskModel.SetCallLater(callLater)

        if wx.PyApp.IsMainLoopRunning():
            wx.CallAfter(ScheduleTask)
        else:
            JobFunc(*args)

    def ShutDown(self):
        """
        Shut down all tasks.
        """
        for task in self.tasksData:
            task.GetCallLater().Stop()

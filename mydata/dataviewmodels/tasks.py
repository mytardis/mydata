import sys
import threading
from datetime import datetime
from datetime import timedelta
import wx.dataview

from mydata.models.task import TaskModel
from mydata.utils.notification import Notification
from mydata.logs import logger


class TasksModel(wx.dataview.PyDataViewIndexListModel):
    def __init__(self, settingsModel):
        self.settingsModel = settingsModel

        self.tasksData = list()

        wx.dataview.PyDataViewIndexListModel.__init__(self,
                                                      len(self.tasksData))

        self.unfilteredTasksData = self.tasksData
        self.filteredTasksData = list()
        self.filtered = False
        self.searchString = ""

        self.columnNames = ("Id", "Job", "Start Time", "Finish Time",
                            "Schedule Type", "Interval (minutes)")
        self.columnKeys = ("dataViewId", "jobDesc", "startTime", "finishTime",
                           "scheduleType", "intervalMinutes")
        self.defaultColumnWidths = (40, 300, 200, 200, 100, 100)

        # This is the largest ID value which has been used in this model.
        # It may no longer exist, i.e. if we delete the row with the
        # largest ID, we don't decrement the maximum ID.
        self.maxDataViewId = 0

    def Filter(self, searchString):
        self.searchString = searchString
        q = self.searchString.lower()
        if not self.filtered:
            # This only does a shallow copy:
            self.unfilteredTasksData = list(self.tasksData)

        for row in reversed(range(0, self.GetRowCount())):
            if q not in self.tasksData[row].GetJobDesc().lower():
                self.filteredTasksData.append(self.tasksData[row])
                del self.tasksData[row]
                # notify the view(s) using this model that it has been removed
                if threading.current_thread().name == "MainThread":
                    self.RowDeleted(row)
                else:
                    wx.CallAfter(self.RowDeleted, row)
                self.filtered = True

        for filteredRow in reversed(range(0, self.GetFilteredRowCount())):
            ftd = self.filteredTasksData[filteredRow]
            if q in ftd.GetJobDesc().lower():
                # Model doesn't care about currently sorted column.
                # Always use ID.
                row = 0
                col = 0
                # Need to get current sort direction
                ascending = True
                while row < self.GetRowCount() and \
                        self.CompareTaskRecords(self.tasksData[row],
                                                ftd, col, ascending) < 0:
                    row = row + 1

                if row == self.GetRowCount():
                    self.tasksData.append(ftd)
                    # Notify the view using this model that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowAppended()
                    else:
                        wx.CallAfter(self.RowAppended)
                else:
                    self.tasksData.insert(row, ftd)
                    # Notify the view using this model that it has been added
                    if threading.current_thread().name == "MainThread":
                        self.RowInserted(row)
                    else:
                        wx.CallAfter(self.RowInserted, row)
                del self.filteredTasksData[filteredRow]
                if self.GetFilteredRowCount() == 0:
                    self.filtered = False

    # All of our columns are strings.  If the model or the renderers
    # in the view are other types then that should be reflected here.
    def GetColumnType(self, col):
        return "string"

    # This method is called to provide the tasksData object for a
    # particular row, col
    def GetValueByRow(self, row, col):
        columnKey = self.GetColumnKeyName(col)
        value = self.tasksData[row].GetValueForKey(columnKey)
        if value is None:
            return ""
        elif columnKey in ("startTime", "finishTime"):
            timeString = value.strftime("%I:%M:%S %p")
            dateString = "{d.day}/{d.month}/{d.year}".format(d=value)
            return value.strftime("%s on %s" % (timeString, dateString))
        return str(value)

    def GetValuesForColname(self, colname):
        values = []
        for col in range(0, self.GetColumnCount()):
            if self.GetColumnName(col) == colname:
                break
        if col == self.GetColumnCount():
            return None

        for row in range(0, self.GetRowCount()):
            values.append(self.GetValueByRow(row, col))
        return values

    def GetColumnName(self, col):
        return self.columnNames[col]

    def GetColumnKeyName(self, col):
        return self.columnKeys[col]

    def GetDefaultColumnWidth(self, col):
        return self.defaultColumnWidths[col]

    # Report how many rows this model provides data for.
    def GetRowCount(self):
        return len(self.tasksData)

    # Report how many rows this model provides data for.
    def GetUnfilteredRowCount(self):
        return len(self.unfilteredTasksData)

    # Report how many rows this model provides data for.
    def GetFilteredRowCount(self):
        return len(self.filteredTasksData)

    # Report how many columns this model provides data for.
    def GetColumnCount(self):
        return len(self.columnNames)

    # Report the number of rows in the model
    def GetCount(self):
        return len(self.tasksData)

    # Called to check if non-standard attributes should be used in the
    # cell at (row, col)
    def GetAttrByRow(self, row, col, attr):
        return False

    # This is called to assist with sorting the data in the view.  The
    # first two args are instances of the DataViewItem class, so we
    # need to convert them to row numbers with the GetRow method.
    # Then it's just a matter of fetching the right values from our
    # data set and comparing them.  The return value is -1, 0, or 1,
    # just like Python's cmp() function.
    def Compare(self, item1, item2, col, ascending):
        # Swap sort order?
        if not ascending:
            item2, item1 = item1, item2
        row1 = self.GetRow(item1)
        row2 = self.GetRow(item2)
        if col == 0:
            return cmp(int(self.GetValueByRow(row1, col)),
                       int(self.GetValueByRow(row2, col)))
        else:
            return cmp(self.GetValueByRow(row1, col),
                       self.GetValueByRow(row2, col))

    # Unlike the previous Compare method, in this case, the task records
    # don't need to be visible in the current (possibly filtered) data view.
    def CompareTaskRecords(self, taskRecord1, taskRecord2, col, ascending):
        if not ascending:
            taskRecord2, taskRecord1 = taskRecord1, taskRecord2
        if col == 0 or col == 3:
            return cmp(int(taskRecord1.GetDataViewId()),
                       int(taskRecord2.GetDataViewId()))
        else:
            return cmp(taskRecord1.GetValueForKey(self.columnKeys[col]),
                       taskRecord2.GetValueForKey(self.columnKeys[col]))

    def DeleteRows(self, rows):
        # Ensure that we save the largest ID used so far:
        self.GetMaxDataViewId()

        # make a copy since we'll be sorting(mutating) the list
        rows = list(rows)
        # use reverse order so the indexes don't change as we remove items
        rows.sort(reverse=True)

        for row in rows:
            del self.tasksData[row]
            del self.unfilteredTasksData[row]

        # Notify the view(s) using this model that it has been removed
        if threading.current_thread().name == "MainThread":
            self.RowsDeleted(rows)
        else:
            wx.CallAfter(self.RowsDeleted, rows)

    def DeleteAllRows(self):
        rowsDeleted = []
        for row in reversed(range(0, self.GetCount())):
            del self.tasksData[row]
            rowsDeleted.append(row)

        # notify the view(s) using this model that it has been removed
        if threading.current_thread().name == "MainThread":
            self.RowsDeleted(rowsDeleted)
        else:
            wx.CallAfter(self.RowsDeleted, rowsDeleted)

        self.unfilteredTasksData = list()
        self.filteredTasksData = list()
        self.filtered = False
        self.searchString = ""
        self.maxDataViewId = 0

    def Contains(self, name):
        for row in range(0, self.GetCount()):
            if self.tasksData[row].GetJobDesc().strip() == name:
                return True
        return False

    def GetTaskById(self, id):
        for row in range(0, self.GetRowCount()):
            if self.unfilteredTasksData[row].GetId() == id:
                return self.unfilteredTasksData[row]
        return None

    def GetMaxDataViewIdFromExistingRows(self):
        maxDataViewId = 0
        for row in range(0, self.GetCount()):
            if self.tasksData[row].GetDataViewId() > maxDataViewId:
                maxDataViewId = self.tasksData[row].GetDataViewId()
        return maxDataViewId

    def GetMaxDataViewId(self):
        if self.GetMaxDataViewIdFromExistingRows() > self.maxDataViewId:
            self.maxDataViewId = self.GetMaxDataViewIdFromExistingRows()
        return self.maxDataViewId

    def AddRow(self, taskModel):
        self.Filter("")
        self.tasksData.append(taskModel)
        # Notify views
        if threading.current_thread().name == "MainThread":
            self.RowAppended()
        else:
            wx.CallAfter(self.RowAppended)

        def jobFunc(taskModel, tasksModel, row, col):

            def taskJobFunc():
                assert callable(taskModel.GetJobFunc())
                title = "Starting"
                message = taskModel.GetJobDesc()
                Notification.notify(message, title=title)
                taskModel.GetJobFunc()(*taskModel.GetJobArgs())
                taskModel.SetFinishTime(datetime.now())
                title = "Finished"
                message = taskModel.GetJobDesc()
                Notification.notify(message, title=title)
                wx.CallAfter(tasksModel.RowValueChanged, row, col)
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
                    dateString = \
                        "{d.day}/{d.month}/{d.year}".format(d=newStartTime)
                    wx.CallAfter(wx.GetApp().frame.SetStatusMessage,
                                 "The \"%s\" task is scheduled "
                                 "to run at %s on %s "
                                 "(recurring every %d minutes)"
                                 % (taskModel.GetJobDesc(),
                                    timeString, dateString, intervalMinutes))
                    tasksModel.AddRow(newTaskModel)
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
                    dateString = \
                        "{d.day}/{d.month}/{d.year}".format(d=newStartTime)
                    wx.CallAfter(wx.GetApp().frame.SetStatusMessage,
                                 "The \"%s\" task is scheduled "
                                 "to run at %s on %s "
                                 "(recurring daily)"
                                 % (taskModel.GetJobDesc(),
                                    timeString, dateString))
                    tasksModel.AddRow(newTaskModel)

            thread = threading.Thread(target=taskJobFunc)
            logger.debug("Starting task %s" % taskModel.GetJobDesc())
            thread.start()

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

        def scheduleTask():
            callLater = wx.CallLater(millis, jobFunc, *args)
            taskModel.SetCallLater(callLater)

        wx.CallAfter(scheduleTask)

        self.unfilteredTasksData = self.tasksData
        self.filteredTasksData = list()
        self.Filter(self.searchString)

    def ShutDown(self):
        for task in self.tasksData:
            task.GetCallLater().Stop()

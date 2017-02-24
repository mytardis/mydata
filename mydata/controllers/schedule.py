"""
mydata/controllers/schedule.py

Functionality for scheduling tasks.
"""

from datetime import timedelta
from datetime import datetime
import sys
import time

import wx

from mydata.models.task import TaskModel
from mydata.models.settings import LastSettingsUpdateTrigger
from mydata.logs import logger


def ScanAndUploadTask(event, needToValidateSettings, jobId, testRun=False):
    """
    Task to be run according to the schedule.
    """
    app = wx.GetApp()
    if wx.PyApp.IsMainLoopRunning():
        wx.CallAfter(app.DisableTestAndUploadToolbarButtons)
        while not app.Processing():
            time.sleep(0.01)
        wx.CallAfter(app.OnRefresh, event, needToValidateSettings,
                     jobId, testRun)
        while app.Processing():
            time.sleep(0.01)
    else:
        app.OnRefresh(event, needToValidateSettings, jobId, testRun)


def HandleValueError(err):
    """
    Handle ValueError when adding task to Tasks Model
    """
    if wx.PyApp.IsMainLoopRunning():
        wx.MessageBox(str(err), "MyData", wx.ICON_ERROR)
    else:
        logger.error(str(err))


class ScheduleController(object):
    """
    Functionality for scheduling tasks.
    """
    def __init__(self, settingsModel, tasksModel):
        self.settingsModel = settingsModel
        self.tasksModel = tasksModel

    def ApplySchedule(self, event, runManually=False,
                      needToValidateSettings=True, testRun=False):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        logger.debug("runManually: %s" % str(runManually))
        scheduleType = self.settingsModel.schedule.scheduleType
        logger.debug("Schedule Type: %s" % scheduleType)
        if scheduleType == "On Startup" and \
                self.settingsModel.lastSettingsUpdateTrigger == \
                LastSettingsUpdateTrigger.READ_FROM_DISK:
            self.CreateOnStartupTask(event, needToValidateSettings)
        elif scheduleType == "On Settings Saved" and \
                self.settingsModel.lastSettingsUpdateTrigger == \
                LastSettingsUpdateTrigger.UI_RESPONSE:
            self.CreateOnSettingsSavedTask(event)
        elif scheduleType == "Manually":
            logger.debug("Schedule type is Manually.")
            if not runManually:
                # Wait for user to manually click Refresh on MyData's toolbar.
                logger.debug("Finished processing schedule type.")
                return
            self.CreateManualTask(event, needToValidateSettings, testRun)
        elif scheduleType == "Once":
            self.CreateOnceTask(event, needToValidateSettings)
        elif scheduleType == "Daily":
            self.CreateDailyTask(event, needToValidateSettings)
        elif scheduleType == "Weekly":
            self.CreateWeeklyTask(event, needToValidateSettings)
        elif scheduleType == "Timer":
            self.CreateTimerTask(event, needToValidateSettings)
        logger.debug("Finished processing schedule type.")

    def CreateOnStartupTask(self, event, needToValidateSettings):
        """
        Create a task to be run automatically when MyData is launched.
        """
        scheduleType = "On Startup"
        logger.debug("Schedule type is %s." % scheduleType)
        jobDesc = "Scan folders and upload datafiles"
        # Wait a few seconds to give the user a chance to
        # read the initial MyData notification before
        # starting the task.
        startTime = datetime.now() + timedelta(seconds=5)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s" % (jobDesc, timeString, dateString))
        if wx.PyApp.IsMainLoopRunning():
            wx.GetApp().GetMainFrame().SetStatusMessage(msg)
        else:
            sys.stderr.write("%s\n" % msg)
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, needToValidateSettings, taskDataViewId]
        task = TaskModel(taskDataViewId, ScanAndUploadTask, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType)
        try:
            self.tasksModel.AddRow(task)
        except ValueError as err:
            HandleValueError(err)

    def CreateOnSettingsSavedTask(self, event):
        """
        Create a task to run after the Settings dialog's OK button has been
        pressed and settings have been validated.
        """
        scheduleType = "On Settings Saved"
        logger.debug("Schedule type is %s." % scheduleType)
        jobDesc = "Scan folders and upload datafiles"
        startTime = datetime.now() + timedelta(seconds=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s" % (jobDesc, timeString, dateString))
        if wx.PyApp.IsMainLoopRunning():
            wx.GetApp().GetMainFrame().SetStatusMessage(msg)
        else:
            sys.stderr.write("%s\n" % msg)
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        needToValidateSettings = False
        jobArgs = [event, needToValidateSettings, taskDataViewId]
        task = TaskModel(taskDataViewId, ScanAndUploadTask, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType)
        try:
            self.tasksModel.AddRow(task)
        except ValueError as err:
            HandleValueError(err)

    def CreateManualTask(self, event, needToValidateSettings=True,
                         testRun=False):
        """
        Create a task to run when the user manually asks MyData to being
        the data folder scans and uploads, usually by clicking the
        Upload toolbar icon, or by selecting the task bar icon menu's
        "Sync Now" menu item.
        """
        scheduleType = "Manual"
        jobDesc = "Scan folders and upload datafiles"
        startTime = datetime.now() + timedelta(seconds=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s" % (jobDesc, timeString, dateString))
        if wx.PyApp.IsMainLoopRunning():
            wx.GetApp().GetMainFrame().SetStatusMessage(msg)
        else:
            sys.stderr.write("%s\n" % msg)
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, needToValidateSettings, taskDataViewId, testRun]
        task = TaskModel(taskDataViewId, ScanAndUploadTask, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType)
        try:
            self.tasksModel.AddRow(task)
        except ValueError as err:
            HandleValueError(err)

    def CreateOnceTask(self, event, needToValidateSettings):
        """
        Create a task to be run once, on the date and time configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "Once"
        logger.debug("Schedule type is Once.")
        jobDesc = "Scan folders and upload datafiles"
        startTime = \
            datetime.combine(self.settingsModel.schedule.scheduledDate,
                             self.settingsModel.schedule.scheduledTime)
        if startTime < datetime.now():
            delta = datetime.now() - startTime
            if delta.total_seconds() < 10:
                startTime = datetime.now() + timedelta(seconds=10)
            else:
                message = "Scheduled time is in the past."
                logger.error(message)
                if self.settingsModel.lastSettingsUpdateTrigger != \
                        LastSettingsUpdateTrigger.READ_FROM_DISK:
                    if wx.PyApp.IsMainLoopRunning():
                        wx.MessageBox(message, "MyData", wx.ICON_ERROR)
                return
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s" % (jobDesc, timeString, dateString))
        if wx.PyApp.IsMainLoopRunning():
            wx.GetApp().GetMainFrame().SetStatusMessage(msg)
        else:
            sys.stderr.write("%s\n" % msg)
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, needToValidateSettings, taskDataViewId]
        task = TaskModel(taskDataViewId, ScanAndUploadTask, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType)
        try:
            self.tasksModel.AddRow(task)
        except ValueError as err:
            HandleValueError(err)

    def CreateDailyTask(self, event, needToValidateSettings):
        """
        Create a task to be run every day at the time specified
        in the Schedule tab of the Settings dialog.
        """
        scheduleType = "Daily"
        logger.debug("Schedule type is Daily.")
        jobDesc = "Scan folders and upload datafiles"
        startTime = \
            datetime.combine(datetime.date(datetime.now()),
                             self.settingsModel.schedule.scheduledTime)
        if startTime < datetime.now():
            startTime = startTime + timedelta(days=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s (recurring daily)"
               % (jobDesc, timeString, dateString))
        if wx.PyApp.IsMainLoopRunning():
            wx.GetApp().GetMainFrame().SetStatusMessage(msg)
        else:
            sys.stderr.write("%s\n" % msg)
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, needToValidateSettings, taskDataViewId]
        task = TaskModel(taskDataViewId, ScanAndUploadTask, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType)
        try:
            self.tasksModel.AddRow(task)
        except ValueError as err:
            HandleValueError(err)

    def CreateWeeklyTask(self, event, needToValidateSettings):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "Weekly"
        logger.debug("Schedule type is Weekly.")
        jobDesc = "Scan folders and upload datafiles"
        days = [self.settingsModel.schedule.mondayChecked,
                self.settingsModel.schedule.tuesdayChecked,
                self.settingsModel.schedule.wednesdayChecked,
                self.settingsModel.schedule.thursdayChecked,
                self.settingsModel.schedule.fridayChecked,
                self.settingsModel.schedule.saturdayChecked,
                self.settingsModel.schedule.sundayChecked]
        if not max(days):
            logger.warning("No days selected for weekly schedule.")
            return
        startTime = \
            datetime.combine(datetime.date(datetime.now()),
                             self.settingsModel.schedule.scheduledTime)
        while not days[startTime.weekday()]:
            startTime = startTime + timedelta(days=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s (recurring on specified days)"
               % (jobDesc, timeString, dateString))
        if wx.PyApp.IsMainLoopRunning():
            wx.GetApp().GetMainFrame().SetStatusMessage(msg)
        else:
            sys.stderr.write("%s\n" % msg)
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, needToValidateSettings, taskDataViewId]
        task = TaskModel(taskDataViewId, ScanAndUploadTask, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType,
                         days=days)
        try:
            self.tasksModel.AddRow(task)
        except ValueError as err:
            HandleValueError(err)

    def CreateTimerTask(self, event, needToValidateSettings):
        """
        Create a task to be run every n minutes, where n is the interval
        specified in the Schedule tab of the Settings dialog.
        """
        scheduleType = "Timer"
        logger.debug("Schedule type is Timer.")
        jobDesc = "Scan folders and upload datafiles"
        intervalMinutes = self.settingsModel.schedule.timerMinutes
        if self.settingsModel.lastSettingsUpdateTrigger == \
                LastSettingsUpdateTrigger.READ_FROM_DISK:
            startTime = datetime.now() + timedelta(seconds=5)
        else:
            # LastSettingsUpdateTrigger.UI_RESPONSE
            startTime = datetime.now() + timedelta(seconds=1)
        timeString = startTime.strftime("%I:%M:%S %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s (recurring every %d minutes)" %
               (jobDesc, timeString, dateString, intervalMinutes))
        if wx.PyApp.IsMainLoopRunning():
            wx.GetApp().GetMainFrame().SetStatusMessage(msg)
        else:
            sys.stderr.write("%s\n" % msg)
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, needToValidateSettings, taskDataViewId]
        task = TaskModel(taskDataViewId, ScanAndUploadTask, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType,
                         intervalMinutes=intervalMinutes)
        try:
            self.tasksModel.AddRow(task)
        except ValueError as err:
            HandleValueError(err)

"""
mydata/controllers/schedule.py

Functionality for scheduling tasks.
"""

from datetime import timedelta
from datetime import datetime
import time

import wx

from mydata.models.task import TaskModel
from mydata.models.settings import LastSettingsUpdateTrigger
from mydata.logs import logger


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
        logger.debug("Getting schedule type from settings dialog.")
        scheduleType = self.settingsModel.GetScheduleType()
        if scheduleType == "On Startup" and \
                self.settingsModel.GetLastSettingsUpdateTrigger() == \
                LastSettingsUpdateTrigger.READ_FROM_DISK:
            self.CreateOnStartupTask(event)
        elif scheduleType == "On Settings Saved" and \
                self.settingsModel.GetLastSettingsUpdateTrigger() == \
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
            self.CreateOnceTask(event)
        elif scheduleType == "Daily":
            self.CreateDailyTask(event)
        elif scheduleType == "Weekly":
            self.CreateWeeklyTask(event)
        elif scheduleType == "Timer":
            self.CreateTimerTask(event)
        logger.debug("Finished processing schedule type.")

    def CreateOnStartupTask(self, event):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "On Startup"
        logger.debug("Schedule type is %s." % scheduleType)

        def OnStartup(event, jobId):
            """
            Task to be run automatically when MyData is launched.
            """
            app = wx.GetApp()
            wx.CallAfter(app.DisableTestAndUploadToolbarButtons)
            while not app.Processing():
                time.sleep(0.01)
            needToValidateSettings = False
            wx.CallAfter(app.OnRefresh, event, needToValidateSettings,
                         jobId)
            # Sleep this thread until the job is really
            # finished, so we can determine the job's
            # finish time.
            while app.Processing():
                time.sleep(0.01)

        jobDesc = "Scan folders and upload datafiles"
        # Wait a few seconds to give the user a chance to
        # read the initial MyData notification before
        # starting the task.
        startTime = datetime.now() + timedelta(seconds=5)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        wx.GetApp().GetMainFrame().SetStatusMessage(
            "The \"%s\" task is scheduled "
            "to run at %s on %s" % (jobDesc, timeString, dateString))
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, taskDataViewId]
        task = TaskModel(taskDataViewId, OnStartup, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType)
        try:
            self.tasksModel.AddRow(task)
        except ValueError, err:
            wx.MessageBox(str(err), "MyData", wx.ICON_ERROR)
            return

    def CreateOnSettingsSavedTask(self, event):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "On Settings Saved"
        logger.debug("Schedule type is %s." % scheduleType)

        def OnSettingsSaved(event, jobId):
            """
            Task to run after the Settings dialog's OK button has been
            pressed and settings have been validated.
            """
            app = wx.GetApp()
            wx.CallAfter(app.DisableTestAndUploadToolbarButtons)
            while not app.Processing():
                time.sleep(0.01)
            needToValidateSettings = False
            wx.CallAfter(app.OnRefresh, event, needToValidateSettings,
                         jobId)
            # Sleep this thread until the job is really
            # finished, so we can determine the job's
            # finish time.
            while app.Processing():
                time.sleep(0.01)

        jobDesc = "Scan folders and upload datafiles"
        startTime = datetime.now() + timedelta(seconds=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        wx.GetApp().GetMainFrame().SetStatusMessage(
            "The \"%s\" task is scheduled "
            "to run at %s on %s" % (jobDesc, timeString, dateString))
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, taskDataViewId]
        task = TaskModel(taskDataViewId, OnSettingsSaved, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType)
        try:
            self.tasksModel.AddRow(task)
        except ValueError, err:
            wx.MessageBox(str(err), "MyData", wx.ICON_ERROR)
            return

    def CreateManualTask(self, event, needToValidateSettings=True,
                         testRun=False):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "Manual"

        def RunTaskManually(event, jobId, needToValidateSettings=True):
            """
            Task to run when the user manually asks MyData to being the
            data folder scans and uploads, usually by clicking the Refresh
            toolbar icon, or by selecting the task bar icon menu's
            "Sync Now" menu item.
            """
            app = wx.GetApp()
            wx.CallAfter(app.DisableTestAndUploadToolbarButtons)
            while not app.Processing():
                time.sleep(0.01)
            wx.CallAfter(app.OnRefresh, event, needToValidateSettings,
                         jobId, testRun)
            # Sleep this thread until the job is really
            # finished, so we can determine the job's
            # finish time.
            while app.Processing():
                time.sleep(0.01)

        jobDesc = "Scan folders and upload datafiles"
        startTime = datetime.now() + timedelta(seconds=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        wx.GetApp().GetMainFrame().SetStatusMessage(
            "The \"%s\" task is scheduled "
            "to run at %s on %s" % (jobDesc, timeString, dateString))
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, taskDataViewId, needToValidateSettings]
        task = TaskModel(taskDataViewId, RunTaskManually, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType)
        try:
            self.tasksModel.AddRow(task)
        except ValueError, err:
            wx.MessageBox(str(err), "MyData", wx.ICON_ERROR)
            return

    def CreateOnceTask(self, event):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "Once"
        logger.debug("Schedule type is Once.")

        def RunTaskOnce(event, jobId):
            """
            Run a task once, on the date and time configured in the
            Schedule tab of the Settings dialog.
            """
            app = wx.GetApp()
            wx.CallAfter(app.DisableTestAndUploadToolbarButtons)
            while not app.Processing():
                time.sleep(0.01)
            needToValidateSettings = False
            wx.CallAfter(app.OnRefresh, event, needToValidateSettings,
                         jobId)
            # Sleep this thread until the job is really
            # finished, so we can determine the job's
            # finish time.
            while app.Processing():
                time.sleep(0.01)

        jobDesc = "Scan folders and upload datafiles"
        startTime = \
            datetime.combine(self.settingsModel.GetScheduledDate(),
                             self.settingsModel.GetScheduledTime())
        if startTime < datetime.now():
            delta = datetime.now() - startTime
            if delta.total_seconds() < 10:
                startTime = datetime.now()
            else:
                message = "Scheduled time is in the past."
                logger.error(message)
                if self.settingsModel.GetLastSettingsUpdateTrigger() != \
                        LastSettingsUpdateTrigger.READ_FROM_DISK:
                    wx.MessageBox(message, "MyData", wx.ICON_ERROR)
                return
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        wx.GetApp().GetMainFrame().SetStatusMessage(
            "The \"%s\" task is scheduled "
            "to run at %s on %s" % (jobDesc, timeString, dateString))
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, taskDataViewId]
        task = TaskModel(taskDataViewId, RunTaskOnce, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType)
        try:
            self.tasksModel.AddRow(task)
        except ValueError, err:
            wx.MessageBox(str(err), "MyData", wx.ICON_ERROR)
            return

    def CreateDailyTask(self, event):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "Daily"
        logger.debug("Schedule type is Daily.")

        def RunTaskDaily(event, jobId):
            """
            Run a task every day at the time specified
            in the Schedule tab of the Settings dialog.
            """
            app = wx.GetApp()
            wx.CallAfter(app.DisableTestAndUploadToolbarButtons)
            while not app.Processing():
                time.sleep(0.01)
            needToValidateSettings = False
            wx.CallAfter(app.OnRefresh, event, needToValidateSettings,
                         jobId)
            # Sleep this thread until the job is really
            # finished, so we can determine the job's
            # finish time.
            while app.Processing():
                time.sleep(0.01)

        jobDesc = "Scan folders and upload datafiles"
        startTime = \
            datetime.combine(datetime.date(datetime.now()),
                             self.settingsModel.GetScheduledTime())
        if startTime < datetime.now():
            startTime = startTime + timedelta(days=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        wx.GetApp().GetMainFrame().SetStatusMessage(
            "The \"%s\" task is scheduled "
            "to run at %s on %s (recurring daily)"
            % (jobDesc, timeString, dateString))
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, taskDataViewId]
        task = TaskModel(taskDataViewId, RunTaskDaily, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType)
        try:
            self.tasksModel.AddRow(task)
        except ValueError, err:
            wx.MessageBox(str(err), "MyData", wx.ICON_ERROR)
            return

    def CreateWeeklyTask(self, event):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "Weekly"
        logger.debug("Schedule type is Weekly.")

        def RunTaskWeekly(event, jobId):
            """
            Run a task on the days (of the week) and time specified
            in the Schedule tab of the Settings dialog.
            """
            app = wx.GetApp()
            wx.CallAfter(app.DisableTestAndUploadToolbarButtons)
            while not app.Processing():
                time.sleep(0.01)
            needToValidateSettings = False
            wx.CallAfter(app.OnRefresh, event, needToValidateSettings,
                         jobId)
            # Sleep this thread until the job is really
            # finished, so we can determine the job's
            # finish time.
            while app.Processing():
                time.sleep(0.01)

        jobDesc = "Scan folders and upload datafiles"
        days = [self.settingsModel.IsMondayChecked(),
                self.settingsModel.IsTuesdayChecked(),
                self.settingsModel.IsWednesdayChecked(),
                self.settingsModel.IsThursdayChecked(),
                self.settingsModel.IsFridayChecked(),
                self.settingsModel.IsSaturdayChecked(),
                self.settingsModel.IsSundayChecked()]
        if not max(days):
            logger.warning("No days selected for weekly schedule.")
            return
        startTime = \
            datetime.combine(datetime.date(datetime.now()),
                             self.settingsModel.GetScheduledTime())
        while not days[startTime.weekday()]:
            startTime = startTime + timedelta(days=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        wx.GetApp().GetMainFrame().SetStatusMessage(
            "The \"%s\" task is scheduled "
            "to run at %s on %s (recurring on specified days)"
            % (jobDesc, timeString, dateString))
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, taskDataViewId]
        task = TaskModel(taskDataViewId, RunTaskWeekly, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType,
                         days=days)
        try:
            self.tasksModel.AddRow(task)
        except ValueError, err:
            wx.MessageBox(str(err), "MyData", wx.ICON_ERROR)
            return

    def CreateTimerTask(self, event):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "Timer"
        logger.debug("Schedule type is Timer.")

        def RunTaskOnTimer(event, jobId):
            """
            Run a task every n minutes, where n is the interval
            specified in the Schedule tab of the Settings dialog.
            """
            app = wx.GetApp()
            wx.CallAfter(app.DisableTestAndUploadToolbarButtons)
            while not app.Processing():
                time.sleep(0.01)
            needToValidateSettings = False
            wx.CallAfter(app.OnRefresh, event, needToValidateSettings,
                         jobId)
            # Sleep this thread until the job is really
            # finished, so we can determine the job's
            # finish time.
            while app.Processing():
                time.sleep(0.01)

        jobDesc = "Scan folders and upload datafiles"
        intervalMinutes = self.settingsModel.GetTimerMinutes()
        if self.settingsModel.GetLastSettingsUpdateTrigger() == \
                LastSettingsUpdateTrigger.READ_FROM_DISK:
            startTime = datetime.now() + timedelta(seconds=5)
        else:
            # LastSettingsUpdateTrigger.UI_RESPONSE
            startTime = datetime.now() + timedelta(seconds=1)
        timeString = startTime.strftime("%I:%M:%S %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        wx.GetApp().GetMainFrame().SetStatusMessage(
            "The \"%s\" task is scheduled "
            "to run at %s on %s (recurring every %d minutes)" %
            (jobDesc, timeString, dateString, intervalMinutes))
        taskDataViewId = self.tasksModel.GetMaxDataViewId() + 1
        jobArgs = [event, taskDataViewId]
        task = TaskModel(taskDataViewId, RunTaskOnTimer, jobArgs, jobDesc,
                         startTime, scheduleType=scheduleType,
                         intervalMinutes=intervalMinutes)
        try:
            self.tasksModel.AddRow(task)
        except ValueError, err:
            wx.MessageBox(str(err), "MyData", wx.ICON_ERROR)
            return

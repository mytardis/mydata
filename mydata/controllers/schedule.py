"""
mydata/controllers/schedule.py

Functionality for scheduling tasks.
"""

from datetime import timedelta
from datetime import datetime
import sys
import time

import wx

from ..dataviewmodels.dataview import DATAVIEW_MODELS
from ..events.start import StartScansAndUploads
from ..settings import SETTINGS
from ..models.task import TaskModel
from ..models.settings import LastSettingsUpdateTrigger
from ..logs import logger

# Default description for jobs created here:
JOB_DESC = "Scan folders and upload datafiles"


def ScanAndUploadTask(event, needToValidateSettings, jobId):
    """
    Task to be run according to the schedule.
    """
    app = wx.GetApp()
    if wx.PyApp.IsMainLoopRunning():
        wx.CallAfter(app.frame.toolbar.DisableTestAndUploadToolbarButtons)
        while not app.Processing():
            time.sleep(0.01)
        wx.CallAfter(StartScansAndUploads, event, needToValidateSettings,
                     jobId)
        while app.Processing():
            time.sleep(0.01)
    else:
        StartScansAndUploads(event, needToValidateSettings, jobId)


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

    @staticmethod
    def ApplySchedule(event, runManually=False, needToValidateSettings=True):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = SETTINGS.schedule.scheduleType
        if runManually:
            logger.debug("runManually: %s" % str(runManually))
            ScheduleController.CreateManualTask(event, needToValidateSettings)
        elif scheduleType != "Manually":
            logger.debug("Schedule Type: %s" % scheduleType)
            if scheduleType == "On Startup" and \
                    SETTINGS.lastSettingsUpdateTrigger == LastSettingsUpdateTrigger.READ_FROM_DISK:
                ScheduleController.CreateOnStartupTask(event, needToValidateSettings)
            elif scheduleType == "On Settings Saved" and \
                    SETTINGS.lastSettingsUpdateTrigger == LastSettingsUpdateTrigger.UI_RESPONSE:
                ScheduleController.CreateOnSettingsSavedTask(event)
            elif scheduleType == "Once":
                ScheduleController.CreateOnceTask(event, needToValidateSettings)
            elif scheduleType == "Daily":
                ScheduleController.CreateDailyTask(event, needToValidateSettings)
            elif scheduleType == "Weekly":
                ScheduleController.CreateWeeklyTask(event, needToValidateSettings)
            elif scheduleType == "Timer":
                ScheduleController.CreateTimerTask(event, needToValidateSettings)
        logger.debug("Finished processing schedule type.")

    @staticmethod
    def CreateTask(event, needToValidateSettings, startTime, scheduleType, msg,
                   intervalMinutes=None, days=None):
        """
        Collecting the common functionality for creating tasks for different
        schedule types
        """
        if wx.PyApp.IsMainLoopRunning():
            wx.GetApp().frame.SetStatusMessage(msg)
        else:
            sys.stderr.write("%s\n" % msg)
        taskDataViewId = DATAVIEW_MODELS['tasks'].GetMaxDataViewId() + 1
        jobArgs = [event, needToValidateSettings, taskDataViewId]
        task = TaskModel(taskDataViewId, ScanAndUploadTask, jobArgs, JOB_DESC,
                         startTime, scheduleType, intervalMinutes, days)
        try:
            DATAVIEW_MODELS['tasks'].AddRow(task)
        except ValueError as err:
            HandleValueError(err)

    @staticmethod
    def CreateOnStartupTask(event, needToValidateSettings):
        """
        Called when MyData is launched with the "On Startup" schedule type
        in its MyData.cfg, so the task needs to run immediately
        """
        scheduleType = "On Startup"
        logger.debug("Schedule type is %s." % scheduleType)
        # Wait a few seconds to give the user a chance to
        # read the initial MyData notification before
        # starting the task.
        startTime = datetime.now() + timedelta(seconds=5)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s" % (JOB_DESC, timeString, dateString))
        ScheduleController.CreateTask(
            event, needToValidateSettings, startTime, scheduleType, msg)

    @staticmethod
    def CreateOnSettingsSavedTask(event):
        """
        Create a task to run after the Settings dialog's OK button has been
        pressed and settings have been validated.
        """
        scheduleType = "On Settings Saved"
        logger.debug("Schedule type is %s." % scheduleType)
        startTime = datetime.now() + timedelta(seconds=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s" % (JOB_DESC, timeString, dateString))
        needToValidateSettings = False
        ScheduleController.CreateTask(
            event, needToValidateSettings, startTime, scheduleType, msg)

    @staticmethod
    def CreateManualTask(event, needToValidateSettings=True):
        """
        Create a task to run when the user manually asks MyData to being
        the data folder scans and uploads, usually by clicking the
        Upload toolbar icon, or by selecting the task bar icon menu's
        "Sync Now" menu item.
        """
        scheduleType = "Manual"
        startTime = datetime.now() + timedelta(seconds=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s" % (JOB_DESC, timeString, dateString))
        ScheduleController.CreateTask(
            event, needToValidateSettings, startTime, scheduleType, msg)

    @staticmethod
    def CreateOnceTask(event, needToValidateSettings):
        """
        Create a task to be run once, on the date and time configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "Once"
        logger.debug("Schedule type is Once.")
        startTime = \
            datetime.combine(SETTINGS.schedule.scheduledDate,
                             SETTINGS.schedule.scheduledTime)
        if startTime < datetime.now():
            delta = datetime.now() - startTime
            if delta.total_seconds() < 10:
                startTime = datetime.now() + timedelta(seconds=10)
            else:
                message = "Scheduled time is in the past."
                logger.error(message)
                if SETTINGS.lastSettingsUpdateTrigger != \
                        LastSettingsUpdateTrigger.READ_FROM_DISK:
                    if wx.PyApp.IsMainLoopRunning():
                        wx.MessageBox(message, "MyData", wx.ICON_ERROR)
                return
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s" % (JOB_DESC, timeString, dateString))
        ScheduleController.CreateTask(
            event, needToValidateSettings, startTime, scheduleType, msg)

    @staticmethod
    def CreateDailyTask(event, needToValidateSettings):
        """
        Create a task to be run every day at the time specified
        in the Schedule tab of the Settings dialog.
        """
        scheduleType = "Daily"
        logger.debug("Schedule type is Daily.")
        startTime = \
            datetime.combine(datetime.date(datetime.now()),
                             SETTINGS.schedule.scheduledTime)
        if startTime < datetime.now():
            startTime = startTime + timedelta(days=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s (recurring daily)"
               % (JOB_DESC, timeString, dateString))
        ScheduleController.CreateTask(
            event, needToValidateSettings, startTime, scheduleType, msg)

    @staticmethod
    def CreateWeeklyTask(event, needToValidateSettings):
        """
        Create and schedule task(s) according to the settings configured in
        the Schedule tab of the Settings dialog.
        """
        scheduleType = "Weekly"
        logger.debug("Schedule type is Weekly.")
        days = [SETTINGS.schedule.mondayChecked,
                SETTINGS.schedule.tuesdayChecked,
                SETTINGS.schedule.wednesdayChecked,
                SETTINGS.schedule.thursdayChecked,
                SETTINGS.schedule.fridayChecked,
                SETTINGS.schedule.saturdayChecked,
                SETTINGS.schedule.sundayChecked]
        if not max(days):
            logger.warning("No days selected for weekly schedule.")
            return
        startTime = \
            datetime.combine(datetime.date(datetime.now()),
                             SETTINGS.schedule.scheduledTime)
        while not days[startTime.weekday()]:
            startTime = startTime + timedelta(days=1)
        timeString = startTime.strftime("%I:%M %p")
        dateString = \
            "{d:%A} {d.day}/{d.month}/{d.year}".format(d=startTime)
        msg = ("The \"%s\" task is scheduled "
               "to run at %s on %s (recurring on specified days)"
               % (JOB_DESC, timeString, dateString))
        ScheduleController.CreateTask(
            event, needToValidateSettings, startTime, scheduleType, msg,
            days=days)

    @staticmethod
    def CreateTimerTask(event, needToValidateSettings):
        """
        Create a task to be run every n minutes, where n is the interval
        specified in the Schedule tab of the Settings dialog.
        """
        scheduleType = "Timer"
        logger.debug("Schedule type is Timer.")
        intervalMinutes = SETTINGS.schedule.timerMinutes
        if SETTINGS.lastSettingsUpdateTrigger == \
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
               (JOB_DESC, timeString, dateString, intervalMinutes))
        ScheduleController.CreateTask(
            event, needToValidateSettings, startTime, scheduleType, msg,
            intervalMinutes=intervalMinutes)

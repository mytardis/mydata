"""
Custom logging for MyData allows logging to the Log view of MyData's
main window, and to ~/.MyData_debug_log.txt.  Logs can be submitted
via HTTP POST for analysis by developers / sys admins.
"""

# pylint: disable=missing-docstring
# pylint: disable=fixme

import threading
import logging
from StringIO import StringIO
from ConfigParser import ConfigParser
import HTMLParser
import os
import time
import subprocess
import sys
import inspect
import pkgutil
import traceback

import requests
import wx

from mydata.logs.SubmitDebugReportDialog import SubmitDebugReportDialog
from mydata.logs.wxloghandler import WxLogHandler
from mydata.logs.wxloghandler import EVT_WX_LOG_EVENT


class Logger(object):
    """
    Allows logger.debug(...), logger.info(...) etc. to write to MyData's
    Log window and to ~/.MyData_debug_log.txt
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, name):
        self.name = name
        self.loggerObject = logging.getLogger(self.name)
        self.loggerOutput = None
        self.loggerFileHandler = None
        self.myDataConfigPath = None
        self.level = logging.INFO
        self.ConfigureLogger()
        if not hasattr(sys, "frozen"):
            self.appRootDir = \
                os.path.dirname(pkgutil.get_loader("mydata.MyData").filename)
        self.logTextCtrl = None
        self.pleaseContactMe = False
        self.contactName = ""
        self.contactEmail = ""
        self.comments = ""

    def SetMyDataConfigPath(self, myDataConfigPath):
        self.myDataConfigPath = myDataConfigPath

    def SendLogMessagesToDebugWindowTextControl(self, logTextCtrl):
        self.logTextCtrl = logTextCtrl
        logWindowHandler = WxLogHandler(self.logTextCtrl)
        logWindowHandler.setLevel(self.level)
        logFormatString = "%(asctime)s - %(moduleName)s - %(lineNumber)d - " \
            "%(functionName)s - %(currentThreadName)s - %(levelname)s - " \
            "%(message)s"
        logWindowHandler.setFormatter(logging.Formatter(logFormatString))
        self.loggerObject.addHandler(logWindowHandler)

        self.logTextCtrl.Bind(EVT_WX_LOG_EVENT, self.OnWxLogEvent)

    def ConfigureLogger(self):
        self.loggerObject = logging.getLogger(self.name)
        self.loggerObject.setLevel(self.level)

        self.logFormatString = \
            "%(asctime)s - %(moduleName)s - %(lineNumber)d - " \
            "%(functionName)s - %(currentThreadName)s - %(levelname)s - " \
            "%(message)s"

        # Send all log messages to a string.
        self.loggerOutput = StringIO()
        stringHandler = logging.StreamHandler(stream=self.loggerOutput)
        stringHandler.setLevel(self.level)
        stringHandler.setFormatter(logging.Formatter(self.logFormatString))
        self.loggerObject.addHandler(stringHandler)

        # Finally, send all log messages to a log file.
        self.loggerFileHandler = \
            logging.FileHandler(os.path.join(os.path.expanduser("~"),
                                             ".MyData_debug_log.txt"))
        self.loggerFileHandler.setLevel(self.level)
        self.loggerFileHandler\
            .setFormatter(logging.Formatter(self.logFormatString))
        self.loggerObject.addHandler(self.loggerFileHandler)

    def SetLogFileName(self, logFileName):
        self.loggerObject.removeHandler(self.loggerFileHandler)
        self.loggerFileHandler = \
            logging.FileHandler(os.path.join(os.path.expanduser("~"),
                                             logFileName))
        self.loggerFileHandler.setLevel(self.level)
        self.loggerFileHandler\
            .setFormatter(logging.Formatter(self.logFormatString))
        self.loggerObject.addHandler(self.loggerFileHandler)

    def SetLevel(self, level):
        self.level = level
        self.loggerObject.setLevel(self.level)
        for handler in self.loggerObject.handlers:
            handler.setLevel(self.level)

    def debug(self, message):
        # pylint: disable=invalid-name
        if self.level > logging.DEBUG:
            return
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        if hasattr(sys, "frozen"):
            # pylint: disable=bare-except
            try:
                moduleName = os.path.basename(outerFrames[1])
            except:
                moduleName = outerFrames[1]
        else:
            moduleName = os.path.relpath(outerFrames[1], self.appRootDir)
        extra = {'moduleName':  moduleName,
                 'lineNumber': outerFrames[2],
                 'functionName': outerFrames[3],
                 'currentThreadName': threading.current_thread().name}
        if threading.current_thread().name == "MainThread":
            self.loggerObject.debug(message, extra=extra)
        else:
            wx.CallAfter(self.loggerObject.debug, message, extra=extra)

    def error(self, message):
        # pylint: disable=invalid-name
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        if hasattr(sys, "frozen"):
            # pylint: disable=bare-except
            try:
                moduleName = os.path.basename(outerFrames[1])
            except:
                moduleName = outerFrames[1]
        else:
            moduleName = os.path.relpath(outerFrames[1], self.appRootDir)
        extra = {'moduleName':  moduleName,
                 'lineNumber': outerFrames[2],
                 'functionName': outerFrames[3],
                 'currentThreadName': threading.current_thread().name}
        if threading.current_thread().name == "MainThread":
            self.loggerObject.error(message, extra=extra)
        else:
            wx.CallAfter(self.loggerObject.error, message, extra=extra)

    def warning(self, message):
        # pylint: disable=invalid-name
        if self.level > logging.WARNING:
            return
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        if hasattr(sys, "frozen"):
            # pylint: disable=bare-except
            try:
                moduleName = os.path.basename(outerFrames[1])
            except:
                moduleName = outerFrames[1]
        else:
            moduleName = os.path.relpath(outerFrames[1], self.appRootDir)
        extra = {'moduleName':  moduleName,
                 'lineNumber': outerFrames[2],
                 'functionName': outerFrames[3],
                 'currentThreadName': threading.current_thread().name}
        if threading.current_thread().name == "MainThread":
            self.loggerObject.warning(message, extra=extra)
        else:
            wx.CallAfter(self.loggerObject.warning, message, extra=extra)

    def info(self, message):
        # pylint: disable=invalid-name
        if self.level > logging.INFO:
            return
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        if hasattr(sys, "frozen"):
            # pylint: disable=bare-except
            try:
                moduleName = os.path.basename(outerFrames[1])
            except:
                moduleName = outerFrames[1]
        else:
            moduleName = os.path.relpath(outerFrames[1], self.appRootDir)
        extra = {'moduleName':  moduleName,
                 'lineNumber': outerFrames[2],
                 'functionName': outerFrames[3],
                 'currentThreadName': threading.current_thread().name}
        if threading.current_thread().name == "MainThread":
            self.loggerObject.info(message, extra=extra)
        else:
            wx.CallAfter(self.loggerObject.info, message, extra=extra)

    def testrun(self, message):
        # pylint: disable=invalid-name
        # pylint: disable=no-self-use
        """
        Always use wx.CallAfter, even when called from the MainThread,
        to ensure that log messages appear in a deterministic order.
        """
        wx.CallAfter(wx.GetApp().GetTestRunFrame().WriteLine, message)

    def DumpLog(self, myDataMainFrame, settingsModel, submitDebugLog=False):
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        logger.debug("Logger.DumpLog: Flushing "
                     "self.loggerObject.handlers[0], which is of class: " +
                     self.loggerObject.handlers[0].__class__.__name__)
        self.loggerObject.handlers[0].flush()

        if myDataMainFrame is None:
            logger.debug("Logger.dump_log: Bailing out early, "
                         "because myDataMainFrame is None.")
            return

        self.contactName = settingsModel.GetContactName()
        self.contactEmail = settingsModel.GetContactEmail()

        def ShowSubmitDebugLogDialog():
            dlg = SubmitDebugReportDialog(myDataMainFrame,
                                          "MyData - Submit Debug Log",
                                          self.loggerOutput.getvalue(),
                                          settingsModel)
            try:
                if wx.IsBusy():
                    wx.EndBusyCursor()
                    stoppedBusyCursor = True
                else:
                    stoppedBusyCursor = False
                result = dlg.ShowModal()
                if stoppedBusyCursor:
                    if not wx.IsBusy():
                        wx.BeginBusyCursor()
                myDataMainFrame.submitDebugLog = (result == wx.ID_OK)
                if myDataMainFrame.submitDebugLog:
                    self.contactName = dlg.GetName()
                    self.contactEmail = dlg.GetEmail()
                    self.comments = dlg.GetComments()
                    self.pleaseContactMe = dlg.GetPleaseContactMe()
            finally:
                dlg.Destroy()
                myDataMainFrame.submitDebugLogDialogCompleted = True

        myDataMainFrame.submitDebugLogDialogCompleted = False

        if submitDebugLog:
            if threading.current_thread().name == "MainThread":
                ShowSubmitDebugLogDialog()
            else:
                wx.CallAfter(ShowSubmitDebugLogDialog)
                while not myDataMainFrame.submitDebugLogDialogCompleted:
                    # FIXME: Remove sleeps and use events instead.
                    time.sleep(0.1)

        if submitDebugLog and myDataMainFrame.submitDebugLog:
            self.debug("About to send debug log")

            url = "https://cvl.massive.org.au/cgi-bin/mydata_log_drop.py"

            debugLog = "\n"
            if settingsModel is not None:
                debugLog = debugLog + "Username: " + \
                    settingsModel.GetUsername() + "\n"
            debugLog = debugLog + "Name: %s\n" % self.contactName
            debugLog = debugLog + "Email: %s\n" % self.contactEmail
            debugLog = debugLog + "Contact me? "
            if self.pleaseContactMe:
                debugLog = debugLog + "Yes" + "\n"
            else:
                debugLog = debugLog + "No" + "\n"
            debugLog = debugLog + "Comments:\n\n" + self.comments + "\n\n"
            errorCount = 0
            logLines = self.loggerOutput.getvalue().splitlines(True)
            for line in logLines:
                if "ERROR" in line:
                    if errorCount == 0:
                        debugLog = debugLog + "\n"
                        debugLog = debugLog + "*** ERROR SUMMARY ***\n"
                        debugLog = debugLog + "\n"
                    errorCount += 1
                    if errorCount >= 100:
                        debugLog = debugLog + "\n"
                        debugLog = debugLog + \
                            "*** TRUNCATING ERROR SUMMARY " \
                            "AFTER 100 ERRORS ***\n"
                        break
                    debugLog = debugLog + line
            if errorCount > 0:
                debugLog = debugLog + "\n"
            if len(logLines) <= 5000:
                debugLog = debugLog + self.loggerOutput.getvalue()
            else:
                debugLog = debugLog + "".join(logLines[1:125])
                debugLog = debugLog + "\n\n"
                debugLog = debugLog + \
                    "*** CONTENT REMOVED BECAUSE OF LARGE LOG SIZE ***\n"
                debugLog = debugLog + "\n\n"
                debugLog = debugLog + "".join(logLines[-4000:])
            fileInfo = {"logfile": debugLog}

            # If we are running in an installation then we have to use
            # our packaged cacert.pem file:
            if os.path.exists('cacert.pem'):
                response = requests.post(url, files=fileInfo,
                                         verify="cacert.pem")
            else:
                response = requests.post(url, files=fileInfo)
            if response.status_code >= 200 and response.status_code < 300:
                logger.debug("Debug log was submitted successfully!")
            else:
                logger.error("An error occurred while attempting to submit "
                             "the debug log.")
                logger.error(response.text)

    def OnWxLogEvent(self, event):
        msg = event.message.strip("\r") + "\n"
        self.logTextCtrl.AppendText(msg)
        event.Skip()

logger = Logger("MyData")  # pylint: disable=invalid-name

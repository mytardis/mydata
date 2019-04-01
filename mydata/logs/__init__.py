"""
Custom logging for MyData allows logging to the Log view of MyData's
main window, and to ~/.MyData_debug_log.txt.  Logs can be submitted
via HTTP POST for analysis by developers / sys admins.
"""
# We want logger singleton to be lowercase, and we want logger.info,
# logger.warning etc. methods to be lowercase:
# pylint: disable=invalid-name
import threading
import traceback
import logging
import os
import sys
import inspect

import requests
from requests.exceptions import RequestException
import six
import wx

from .SubmitDebugReportDialog import SubmitDebugReportDialog
from .wxloghandler import WxLogHandler
from .wxloghandler import EVT_WX_LOG_EVENT

if six.PY3:
    from io import StringIO
else:
    from io import BytesIO as StringIO


class MyDataFormatter(logging.Formatter):
    """
    Can be used to handle logging messages coming from non-MyData modules
    which lack the extra attributes.
    """
    def format(self, record):
        """
        Overridden from logging.Formatter class
        """
        if not hasattr(record, 'moduleName'):
            record.moduleName = ''
        if not hasattr(record, 'functionName'):
            record.functionName = ''
        if not hasattr(record, 'currentThreadName'):
            record.currentThreadName = ''
        if not hasattr(record, 'lineNumber'):
            record.lineNumber = 0
        return super(MyDataFormatter, self).format(record)


class Logger(object):
    """
    Allows logger.debug(...), logger.info(...) etc. to write to MyData's
    Log window and to ~/.MyData_debug_log.txt
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, name):
        self.name = name
        self.loggerObject = logging.getLogger(self.name)
        self.formatString = ""
        self.loggerOutput = None
        self.streamHandler = None
        self.fileHandler = None
        self.logWindowHandler = None
        self.level = logging.INFO
        self.ConfigureLogger()
        if not hasattr(sys, "frozen"):
            self.appRootDir = os.path.realpath(
                os.path.join(os.path.dirname(__file__), "..", ".."))
        self.logTextCtrl = None
        self.pleaseContactMe = False
        self.contactName = ""
        self.contactEmail = ""
        self.comments = ""

    def SendLogMessagesToDebugWindowTextControl(self, logTextCtrl):
        """
        Send log messages to debug window text control
        """
        self.logTextCtrl = logTextCtrl
        self.logWindowHandler = WxLogHandler(self.logTextCtrl)
        self.logWindowHandler.setLevel(self.level)
        formatString = "%(asctime)s - %(moduleName)s - %(lineNumber)d - " \
            "%(functionName)s - %(currentThreadName)s - %(levelname)s - " \
            "%(message)s"
        self.logWindowHandler.setFormatter(MyDataFormatter(formatString))
        self.loggerObject.addHandler(self.logWindowHandler)
        if sys.platform.startswith("linux"):
            errandBoyLogger = logging.getLogger("errand_boy.transports.unixsocket")
            errandBoyLogger.addHandler(self.logWindowHandler)

        self.logTextCtrl.Bind(EVT_WX_LOG_EVENT, self.OnWxLogEvent)

    def ConfigureLogger(self):
        """
        Configure logger object
        """
        self.loggerObject = logging.getLogger(self.name)
        self.loggerObject.setLevel(self.level)

        self.formatString = \
            "%(asctime)s - %(moduleName)s - %(lineNumber)d - " \
            "%(functionName)s - %(currentThreadName)s - %(levelname)s - " \
            "%(message)s"

        # Send all log messages to a string.
        self.loggerOutput = StringIO()
        self.streamHandler = logging.StreamHandler(stream=self.loggerOutput)
        self.streamHandler.setLevel(self.level)
        self.streamHandler.setFormatter(MyDataFormatter(self.formatString))
        self.loggerObject.addHandler(self.streamHandler)

        # Finally, send all log messages to a log file.
        if 'MYDATA_DEBUG_LOG_PATH' in os.environ:
            logFilePath = os.path.abspath(os.environ['MYDATA_DEBUG_LOG_PATH'])
            if os.path.isdir(logFilePath):
                logFilePath = os.path.join(logFilePath,
                                           ".MyData_debug_log.txt")
        else:
            logFilePath = os.path.join(os.path.expanduser("~"),
                                       ".MyData_debug_log.txt")
        self.fileHandler = logging.FileHandler(logFilePath)
        self.fileHandler.setLevel(self.level)
        self.fileHandler.setFormatter(MyDataFormatter(self.formatString))
        self.loggerObject.addHandler(self.fileHandler)

    def GetLevel(self):
        """
        Returns the logging level, e.g. logging.DEBUG
        """
        return self.level

    def SetLevel(self, level):
        """
        Sets the logging level, e.g. logging.DEBUG
        """
        self.level = level
        self.loggerObject.setLevel(self.level)
        for handler in self.loggerObject.handlers:
            handler.setLevel(self.level)

    def debug(self, message):
        """
        Log a message with level logging.DEBUG
        """
        if self.level > logging.DEBUG:
            return
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        if hasattr(sys, "frozen"):
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
            self.loggerObject.debug(message.encode(), extra=extra)
        else:
            wx.CallAfter(self.loggerObject.debug, message.encode(), extra=extra)

    def error(self, message):
        """
        Log a message with level logging.ERROR
        """
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        if hasattr(sys, "frozen"):
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
            self.loggerObject.error(message.encode(), extra=extra)
        else:
            wx.CallAfter(self.loggerObject.error, message.encode(), extra=extra)

    def warning(self, message):
        """
        Log a message with level logging.WARNING
        """
        if self.level > logging.WARNING:
            return
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        if hasattr(sys, "frozen"):
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
            self.loggerObject.warning(message.encode(), extra=extra)
        else:
            wx.CallAfter(self.loggerObject.warning, message.encode(), extra=extra)

    def info(self, message):
        """
        Log a message with level logging.INFO
        """
        if self.level > logging.INFO:
            return
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        if hasattr(sys, "frozen"):
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
            self.loggerObject.info(message.encode(), extra=extra)
        else:
            wx.CallAfter(self.loggerObject.info, message.encode(), extra=extra)

    def testrun(self, message):
        # pylint: disable=no-self-use
        """
        Log to the test run window

        Always use wx.CallAfter, even when called from the MainThread,
        to ensure that log messages appear in a deterministic order.
        """
        if wx.PyApp.IsMainLoopRunning():
            wx.CallAfter(wx.GetApp().testRunFrame.WriteLine, message)
        else:
            sys.stderr.write("%s\n" % message)

    def GenerateDebugLogContent(self, settings):
        """
        Generate content for submiting a debug log
        """
        logger.debug("Logger.GenerateDebugLogContent: Flushing "
                     "self.loggerObject.handlers[0], which is of class: " +
                     self.loggerObject.handlers[0].__class__.__name__)
        self.loggerObject.handlers[0].flush()

        debugLog = "\n"
        debugLog += "Username: " + settings.general.username + "\n"
        debugLog += "Name: %s\n" % self.contactName
        debugLog += "Email: %s\n" % self.contactEmail
        debugLog += "Contact me? "
        if self.pleaseContactMe:
            debugLog += "Yes" + "\n"
        else:
            debugLog += "No" + "\n"
        debugLog += "Comments:\n\n" + self.comments + "\n\n"
        errorCount = 0
        logLines = self.loggerOutput.getvalue().splitlines(True)
        for line in logLines:
            if "ERROR" in line:
                if errorCount == 0:
                    debugLog += "\n"
                    debugLog += "*** ERROR SUMMARY ***\n"
                    debugLog += "\n"
                errorCount += 1
                if errorCount >= 100:
                    debugLog += "\n"
                    debugLog += "*** TRUNCATING ERROR SUMMARY " \
                        "AFTER 100 ERRORS ***\n"
                    break
                debugLog += line
        if errorCount > 0:
            debugLog += "\n"
        if len(logLines) <= 5000:
            debugLog += self.loggerOutput.getvalue()
        else:
            debugLog += "".join(logLines[1:125])
            debugLog += "\n\n"
            debugLog += "*** CONTENT REMOVED BECAUSE OF LARGE LOG SIZE ***\n"
            debugLog += "\n\n"
            debugLog += "".join(logLines[-4000:])
        return debugLog

    def GetValue(self):
        """
        Return all logs sent to StringIO handler
        """
        self.streamHandler.flush()
        return self.loggerOutput.getvalue()

    def SubmitLog(self, myDataMainFrame, settings,
                  url="https://cvl.massive.org.au/cgi-bin/mydata_log_drop.py"):
        """
        Open the SubmitDebugReportDialog and submit a debug report if the user
        clicks OK
        """
        # pylint: disable=too-many-branches
        self.contactName = settings.general.contactName
        self.contactEmail = settings.general.contactEmail

        dlg = SubmitDebugReportDialog(
            myDataMainFrame, "MyData - Submit Debug Log",
            self.loggerOutput.getvalue(), settings)
        try:
            if wx.PyApp.IsMainLoopRunning():
                if wx.IsBusy():
                    wx.EndBusyCursor()
                    stoppedBusyCursor = True
                else:
                    stoppedBusyCursor = False
                result = dlg.ShowModal()
                submitDebugLogOK = (result == wx.ID_OK)
                if stoppedBusyCursor:
                    if not wx.IsBusy():
                        wx.BeginBusyCursor()
            else:
                dlg.Show()
                dlg.Hide()
                submitDebugLogOK = True
            if submitDebugLogOK:
                self.contactName = dlg.GetContactName()
                self.contactEmail = dlg.GetContactEmail()
                self.comments = dlg.GetComments()
                self.pleaseContactMe = dlg.GetPleaseContactMe()
        finally:
            dlg.Destroy()

        if submitDebugLogOK:
            self.debug("About to send debug log")
            fileInfo = {"logfile": self.GenerateDebugLogContent(settings)}
            try:
                response = requests.post(
                    url, files=fileInfo,
                    timeout=settings.miscellaneous.connectionTimeout)
                response.raise_for_status()
                logger.info("Debug log was submitted successfully!")
            except RequestException:
                logger.error("An error occurred while attempting to submit "
                             "the debug log.")
                logger.error(traceback.format_exc())

    def OnWxLogEvent(self, event):
        """
        Append log message to the Log View's text control
        """
        msg = event.message.strip("\r") + "\n"
        self.logTextCtrl.AppendText(msg)
        event.Skip()


logger = Logger("MyData")

import threading
import wx
import logging
from StringIO import StringIO
from ConfigParser import ConfigParser
import HTMLParser
import os
import time
import subprocess
import sys
import requests
import inspect

from SubmitDebugReportDialog import SubmitDebugReportDialog


class Logger():
    """
    Allows logger.debug(...), logger.info(...) etc. to write to MyData's
    Log window and to ~/.MyData_debug_log.txt
    """
    def __init__(self, name):
        self.name = name
        self.loggerObject = None
        self.loggerOutput = None
        self.loggerFileHandler = None
        self.myDataConfigPath = None
        self.ConfigureLogger()

    def SetMyDataConfigPath(self, myDataConfigPath):
        self.myDataConfigPath = myDataConfigPath

    def SendLogMessagesToDebugWindowTextControl(self, logTextCtrl):
        try:
            logWindowHandler = logging.StreamHandler(stream=logTextCtrl)
        except:
            logWindowHandler = logging.StreamHandler(strm=logTextCtrl)
        logWindowHandler.setLevel(logging.DEBUG)
        logFormatString = "%(asctime)s - %(moduleName)s - %(functionName)s - " \
            "%(lineNumber)d - %(levelname)s - %(message)s"
        logWindowHandler.setFormatter(logging.Formatter(logFormatString))
        self.loggerObject = logging.getLogger(self.name)
        self.loggerObject.addHandler(logWindowHandler)

    def ConfigureLogger(self):
        self.loggerObject = logging.getLogger(self.name)
        self.loggerObject.setLevel(logging.DEBUG)

        logFormatString = "%(asctime)s - %(moduleName)s - %(functionName)s - " \
            "%(lineNumber)d - %(levelname)s - %(message)s"

        # Send all log messages to a string.
        self.loggerOutput = StringIO()
        try:
            stringHandler = logging.StreamHandler(stream=self.loggerOutput)
        except:
            stringHandler = logging.StreamHandler(strm=self.loggerOutput)
        stringHandler.setLevel(logging.DEBUG)
        stringHandler.setFormatter(logging.Formatter(logFormatString))
        self.loggerObject.addHandler(stringHandler)

        # Finally, send all log messages to a log file.
        from os.path import expanduser, join
        self.loggerFileHandler = \
            logging.FileHandler(join(expanduser("~"), ".MyData_debug_log.txt"))
        self.loggerFileHandler.setLevel(logging.DEBUG)
        self.loggerFileHandler\
            .setFormatter(logging.Formatter(logFormatString))
        self.loggerObject.addHandler(self.loggerFileHandler)

    def debug(self, message):
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        extra = {'moduleName':  os.path.basename(outerFrames[1]),
                 'lineNumber': outerFrames[2],
                 'functionName': outerFrames[3]}
        if threading.current_thread().name == "MainThread":
            self.loggerObject.debug(message, extra=extra)
        else:
            wx.CallAfter(self.loggerObject.debug, message, extra=extra)

    def error(self, message):
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        extra = {'moduleName':  os.path.basename(outerFrames[1]),
                 'lineNumber': outerFrames[2],
                 'functionName': outerFrames[3]}
        if threading.current_thread().name == "MainThread":
            self.loggerObject.error(message, extra=extra)
        else:
            wx.CallAfter(self.loggerObject.error, message, extra=extra)

    def warning(self, message):
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        extra = {'moduleName':  os.path.basename(outerFrames[1]),
                 'lineNumber': outerFrames[2],
                 'functionName': outerFrames[3]}
        if threading.current_thread().name == "MainThread":
            self.loggerObject.warning(message, extra=extra)
        else:
            wx.CallAfter(self.loggerObject.warning, message, extra=extra)

    def info(self, message):
        frame = inspect.currentframe()
        outerFrames = inspect.getouterframes(frame)[1]
        extra = {'moduleName':  os.path.basename(outerFrames[1]),
                 'lineNumber': outerFrames[2],
                 'functionName': outerFrames[3]}
        if threading.current_thread().name == "MainThread":
            self.loggerObject.info(message, extra=extra)
        else:
            wx.CallAfter(self.loggerObject.info, message, extra=extra)

    def DumpLog(self, myDataMainFrame, submitDebugLog=False,
                settingsModel=None):
        logger.debug("Logger.DumpLog: Flushing "
                     "self.loggerObject.handlers[0], which is of class: "
                     + self.loggerObject.handlers[0].__class__.__name__)
        self.loggerObject.handlers[0].flush()

        if myDataMainFrame is None:
            logger.debug("Logger.dump_log: Bailing out early, "
                         "because myDataMainFrame is None.")
            return

        def showSubmitDebugLogDialog():
            dlg = SubmitDebugReportDialog(None, wx.ID_ANY, 'MyData',
                                          self.loggerOutput.getvalue(),
                                          self.myDataConfigPath)
            try:
                if wx.IsBusy():
                    wx.EndBusyCursor()
                    stoppedBusyCursor = True
                else:
                    stoppedBusyCursor = False
                result = dlg.ShowModal()
                if stoppedBusyCursor:
                    wx.BeginBusyCursor()
                myDataMainFrame.submitDebugLog = (result == wx.ID_OK)
                if myDataMainFrame.submitDebugLog:
                    self.name = dlg.getName()
                    self.email = dlg.getEmail()
                    self.comments = dlg.getComments()
                    self.pleaseContactMe = dlg.getPleaseContactMe()
            finally:
                dlg.Destroy()
                myDataMainFrame.submitDebugLogDialogCompleted = True

        myDataMainFrame.submitDebugLogDialogCompleted = False

        if submitDebugLog:
            if threading.current_thread().name == "MainThread":
                showSubmitDebugLogDialog()
            else:
                wx.CallAfter(showSubmitDebugLogDialog)
                while not myDataMainFrame.submitDebugLogDialogCompleted:
                    time.sleep(0.1)

        if submitDebugLog and myDataMainFrame.submitDebugLog:
            self.debug("About to send debug log")

            url = "https://cvl.massive.org.au/cgi-bin/log_drop.py"

            debugLog = "\n"
            if settingsModel is not None:
                debugLog = debugLog + "Username: " + \
                    settingsModel.GetMyTardisUsername() + "\n"
            debugLog = debugLog + "Name: " + self.name + "\n"
            debugLog = debugLog + "Email: " + self.email + "\n"
            debugLog = debugLog + "Contact me? "
            if self.pleaseContactMe:
                debugLog = debugLog + "Yes" + "\n"
            else:
                debugLog = debugLog + "No" + "\n"
            debugLog = debugLog + "Comments:\n\n" + self.comments + "\n\n"
            atLeastOneError = False
            for line in self.loggerOutput.getvalue().splitlines(True):
                if "ERROR" in line:
                    atLeastOneError = True
                    debugLog = debugLog + line
            if atLeastOneError:
                debugLog = debugLog + "\n"
            debugLog = debugLog + self.loggerOutput.getvalue()
            fileInfo = {"logfile": debugLog}

            # If we are running in an installation then we have to use
            # our packaged cacert.pem file:
            if os.path.exists('cacert.pem'):
                r = requests.post(url, files=fileInfo, verify="cacert.pem")
            else:
                r = requests.post(url, files=fileInfo)

logger = Logger("MyData")

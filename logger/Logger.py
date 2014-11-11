import threading
import wx
import logging
from StringIO import StringIO
import HTMLParser
import os
import time
import subprocess
import sys
import requests
from SubmitDebugReportDialog import SubmitDebugReportDialog

class Logger():

    def __init__(self, name):
        self.name = name
        self.loggerObject = None
        self.loggerOutput = None
        self.loggerFileHandler = None
        self.configureLogger()
        self.globalLauncherConfig=None
        self.globalLauncherPreferencesFilePath=None

    def setGlobalLauncherConfig(self, globalLauncherConfig):
        self.globalLauncherConfig = globalLauncherConfig

    def setGlobalLauncherPreferencesFilePath(self, globalLauncherPreferencesFilePath):
        self.globalLauncherPreferencesFilePath = globalLauncherPreferencesFilePath

    def sendLogMessagesToDebugWindowTextControl(self, logTextCtrl):
        # Send all log messages to the debug window, which may or may not be visible.
        try:
            log_window_handler = logging.StreamHandler(stream=logTextCtrl)
        except:
            log_window_handler = logging.StreamHandler(strm=logTextCtrl)
        log_window_handler.setLevel(logging.DEBUG)
        log_format_string = '%(asctime)s - %(name)s - %(module)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
        log_window_handler.setFormatter(logging.Formatter(log_format_string))
        self.loggerObject = logging.getLogger(self.name)
        self.loggerObject.addHandler(log_window_handler)

    def configureLogger(self):
        self.loggerObject = logging.getLogger(self.name)
        self.loggerObject.setLevel(logging.DEBUG)

        log_format_string = '%(asctime)s - %(name)s - %(module)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'

        # Send all log messages to a string.
        self.loggerOutput = StringIO()
        try:
            string_handler = logging.StreamHandler(stream=self.loggerOutput)
        except:
            string_handler = logging.StreamHandler(strm=self.loggerOutput)
        string_handler.setLevel(logging.DEBUG)
        string_handler.setFormatter(logging.Formatter(log_format_string))
        self.loggerObject.addHandler(string_handler)

        # Finally, send all log messages to a log file.
        from os.path import expanduser, join
        self.loggerFileHandler = logging.FileHandler(join(expanduser("~"), '.MyData_debug_log.txt'))
        self.loggerFileHandler.setLevel(logging.DEBUG)
        self.loggerFileHandler.setFormatter(logging.Formatter(log_format_string))
        self.loggerObject.addHandler(self.loggerFileHandler)

    def debug(self, message):
        if threading.current_thread().name=="MainThread":
            self.loggerObject.debug(message)
        else:
            wx.CallAfter(self.loggerObject.debug, message)

    def error(self, message):
        if threading.current_thread().name=="MainThread":
            self.loggerObject.error(message)
        else:
            wx.CallAfter(self.loggerObject.error, message)

    def warning(self, message):
        if threading.current_thread().name=="MainThread":
            self.loggerObject.warning(message)
        else:
            wx.CallAfter(self.loggerObject.warning, message)

    def info(self, message):
        if threading.current_thread().name=="MainThread":
            self.loggerObject.info(message)
        else:
            wx.CallAfter(self.loggerObject.info, message)

    def dump_log(self, instrumentAppMainFrame, submit_log=False, settingsModel = None):
        # Commenting out logging.shutdown() for now,
        # because of concerns that logging could be used
        # after the call to logging.shutdown() which is
        # not allowed.
        # logging.shutdown()
        logger.debug("Logger.dump_log: Flushing self.loggerObject.handlers[0], which is of class: " + self.loggerObject.handlers[0].__class__.__name__)
        self.loggerObject.handlers[0].flush()

        if instrumentAppMainFrame==None:
            logger.debug("Logger.dump_log: Bailing out early, because instrumentAppMainFrame is None.")
            return

        def showSubmitDebugLogDialog():
            dlg = SubmitDebugReportDialog(None,wx.ID_ANY,'MyData',self.loggerOutput.getvalue(),self.globalLauncherConfig,self.globalLauncherPreferencesFilePath)
            try:
                if wx.IsBusy():
                    wx.EndBusyCursor()
                    stoppedBusyCursor = True
                else:
                    stoppedBusyCursor = False
                result = dlg.ShowModal()
                if stoppedBusyCursor:
                    wx.BeginBusyCursor()
                instrumentAppMainFrame.submit_log = result == wx.ID_OK
                if instrumentAppMainFrame.submit_log:
                    self.name = dlg.getName()
                    self.email = dlg.getEmail()
                    self.comments = dlg.getComments()
                    self.pleaseContactMe = dlg.getPleaseContactMe()
            finally:
                dlg.Destroy()
                instrumentAppMainFrame.submitDebugLogDialogCompleted = True

        instrumentAppMainFrame.submitDebugLogDialogCompleted = False

        if submit_log:
            if threading.current_thread().name=="MainThread":
                showSubmitDebugLogDialog()
            else:
                wx.CallAfter(showSubmitDebugLogDialog)
                while not instrumentAppMainFrame.submitDebugLogDialogCompleted:
                    time.sleep(0.1)

        if submit_log and instrumentAppMainFrame.submit_log:
            self.debug('about to send debug log')

            url       = 'https://cvl.massive.org.au/cgi-bin/log_drop.py'

            debugLog = "\n"
            if settingsModel is not None:
                debugLog = debugLog + "Username: " + settingsModel.GetMyTardisUsername() + "\n"
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
            debugLog =  debugLog + self.loggerOutput.getvalue()
            file_info = {'logfile': debugLog}

            # If we are running in an installation then we have to use
            # our packaged cacert.pem file:
            if os.path.exists('cacert.pem'):
                r = requests.post(url, files=file_info, verify='cacert.pem')
            else:
                r = requests.post(url, files=file_info)

logger = Logger("MyData")



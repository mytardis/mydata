import sys
import os
import wx.html
import tempfile
import requests
import traceback
import pkgutil
from logger.Logger import logger
import zipfile

mydataHtmlHelpProjectFilename = "mydata.hhp"


class HelpController():

    def __init__(self):

        # The only way I know how to detect the state of the busy cursor
        # is to try to stop it, and see if this throws an exception.
        try:
            wx.EndBusyCursor()
            self.stoppedBusyCursor = True
        except:
            self.stoppedBusyCursor = False

        wx.BeginBusyCursor()

        self.wxHtmlHelpController = \
            wx.html.HtmlHelpController(style=wx.html.HF_DEFAULT_STYLE,
                                       parentWindow=None)

        self.helpZipFile = None
        self.helpZipFilePath = None
        self.helpZipFileDirectory = None
        self.helpFilesDirectory = None

        self.mydataHelpUrl = \
            "https://github.com/monash-merc/mydata/blob" \
            "/master/help/helpfiles.zip?raw=true"
        self.initializationSucceeded = False
        try:
            # Download helpfiles.zip:

            self.helpZipFile = tempfile.NamedTemporaryFile(mode='w+b',
                                                           prefix='helpfiles-',
                                                           suffix='.zip',
                                                           delete=False)
            self.helpZipFilePath = self.helpZipFile.name
            logger.debug("self.helpZipFilePath = " + self.helpZipFilePath)
            r = requests.get(self.mydataHelpUrl, verify=True)
            if r.status_code == 200:
                for chunk in r.iter_content():
                    self.helpZipFile.write(chunk)
            self.helpZipFile.close()

            # We should be able to add the zip archive directly to the
            # help controller, but that didn't seem to work.

            # Unzip helpfiles.zip:

            self.helpZipFileDirectory, self.helpZipFileFilename = \
                os.path.split(self.helpZipFilePath)
            unzip(self.helpZipFilePath, self.helpZipFileDirectory)
            self.helpFilesDirectory = os.path.join(self.helpZipFileDirectory,
                                                   "helpfiles")
            logger.debug("self.helpFilesDirectory = "
                         + self.helpFilesDirectory)

            self.mydataHtmlHelpProjectFile = \
                os.path.join(self.helpFilesDirectory,
                             mydataHtmlHelpProjectFilename)
            self.initializationSucceeded = \
                self.wxHtmlHelpController\
                    .AddBook(self.mydataHtmlHelpProjectFile)

        except:
            logger.debug(traceback.format_exc())

            try:
                # If we don't succeed in downloading help,
                # we will try using local help files instead.

                if hasattr(sys, 'frozen'):
                    if sys.platform.startswith("darwin"):
                        self.helpFilesDirectory = \
                            os.path.join(os.path.dirname(sys.executable),
                                         "..", "Resources",
                                         "help", "helpfiles")
                    else:
                        self.helpFilesDirectory = \
                            os.path.join(os.path.dirname(sys.executable),
                                         "help", "helpfiles")
                else:
                    mydataModulePath = \
                        os.path.dirname(pkgutil.get_loader("mydata").filename)
                    self.helpFilesDirectory = os.path.join(mydataModulePath,
                                                           "help", "helpfiles")

                self.mydataHtmlHelpProjectFile = \
                    os.path.join(self.helpFilesDirectory,
                                 mydataHtmlHelpProjectFilename)
                self.initializationSucceeded = \
                    self.wxHtmlHelpController\
                        .AddBook(self.mydataHtmlHelpProjectFile)

            except:
                logger.debug(traceback.format_exc())

        if not self.stoppedBusyCursor:
            try:
                wx.EndBusyCursor()
            except:
                pass

    def cleanUp(self):
        if self.helpZipFilePath is not None:
            os.remove(self.helpZipFilePath)
        if self.helpFilesDirectory is not None:
            for helpFile in os.listdir(self.helpFilesDirectory):
                os.remove(os.path.join(self.helpFilesDirectory, helpFile))
            os.remove(self.helpFilesDirectory)

    # At first I tried inheriting from the wx.html.HtmlHelpController class,
    # so that I would get these methods for free, but then AddBook complained
    # that objects of my derived class were not instances of
    # wx.html.HtmlHelpController

    def DisplayContents(self):
        self.wxHtmlHelpController.DisplayContents()

    def Display(self, chapter):
        self.wxHtmlHelpController.Display(chapter)


def unzip(zipFilePath, destDir):

    zfile = zipfile.ZipFile(zipFilePath)

    for name in zfile.namelist():

        (dirName, fileName) = os.path.split(name)

        absoluteDirectoryPath = os.path.join(destDir, dirName)
        if not os.path.exists(absoluteDirectoryPath):
            os.mkdir(absoluteDirectoryPath)

        if fileName != '':
            fd = open(os.path.join(absoluteDirectoryPath, fileName), 'wb')
            fd.write(zfile.read(name))
            fd.close()

    zfile.close()

helpController = HelpController()

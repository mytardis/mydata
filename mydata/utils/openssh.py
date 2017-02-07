"""
Methods for using OpenSSH functionality from MyData.
On Windows, we bundle a Cygwin build of OpenSSH.

subprocess is used extensively throughout this module.

Given the complex quoting requirements when running remote
commands over ssh, I don't trust Python's
automatic quoting which is done when converting a list of arguments
to a command string in subprocess.Popen.  Furthermore, formatting
the command string ourselves, rather than leaving it to Python
means that we are restricted to using shell=True in subprocess on
POSIX systems.  shell=False seems to work better on Windows,
otherwise we need to worry about escaping special characters like
'>' with carets (i.e. '^>').

"""

# Disabling some Pylint warnings for now...
# pylint: disable=missing-docstring
# pylint: disable=wrong-import-position

import sys
from datetime import datetime
import os
import subprocess
import traceback
import re
import getpass
import threading
import time
import pkgutil
import struct

import psutil
import requests

if sys.platform.startswith("win"):
    import win32process  # pylint: disable=import-error

from mydata.logs import logger
from mydata.models.datafile import DataFileModel
from mydata.models.replica import ReplicaModel
from mydata.models.upload import UploadStatus
from mydata.utils.exceptions import SshException
from mydata.utils.exceptions import ScpException
from mydata.utils.exceptions import PrivateKeyDoesNotExist
from mydata.utils.exceptions import DoesNotExist

from mydata.utils.exceptions import MissingMyDataReplicaApiEndpoint

if sys.platform.startswith("linux"):
    from mydata.linuxsubprocesses import GetErrandBoyTransport

from mydata.subprocesses import DEFAULT_STARTUP_INFO
from mydata.subprocesses import DEFAULT_CREATION_FLAGS

# Running subprocess's communicate from multiple threads can cause high CPU
# usage, so we poll each subprocess before running communicate, using a sleep
# interval of SLEEP_FACTOR * maxThreads.
SLEEP_FACTOR = 0.01


class OpenSSH(object):
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=no-self-use
    def DoubleQuote(self, string):
        return '"' + string.replace('"', r'\"') + '"'

    def DoubleQuoteRemotePath(self, string):
        path = string.replace('"', r'\"')
        path = path.replace('`', r'\\`')
        path = path.replace('$', r'\\$')
        return '"%s"' % path

    def __init__(self):
        """
        Locate the SSH binaries on various systems. On Windows we bundle a
        Cygwin build of OpenSSH.
        """
        sixtyFourBitPython = (struct.calcsize('P') * 8 == 64)
        sixtyFourBitOperatingSystem = sixtyFourBitPython or \
            (sys.platform.startswith("win") and win32process.IsWow64Process())
        if "HOME" not in os.environ:
            os.environ["HOME"] = os.path.expanduser('~')
        if sixtyFourBitOperatingSystem:
            winOpensshDir = r"win64\openssh-7.3p1-cygwin-2.6.0"
        else:
            winOpensshDir = r"win32\openssh-7.1p1-hpn-14.9-cygwin-2.2.1"
        if hasattr(sys, "frozen"):
            baseDir = os.path.dirname(sys.executable)
        else:
            baseDir = os.path.dirname(pkgutil.get_loader("mydata").filename)
            winOpensshDir = os.path.join("resources", winOpensshDir)
        if sys.platform.startswith("win"):
            baseDir = os.path.join(baseDir, winOpensshDir)
            self.preferToUseShellInSubprocess = False
            binarySuffix = ".exe"
            dotSshDir = os.path.join(
                baseDir, "home", getpass.getuser(), ".ssh")
            if not os.path.exists(dotSshDir):
                os.makedirs(dotSshDir)
        else:
            # Using subprocess's shell=True below should be reviewed.
            # Don't change it without testing quoting of special characters.
            baseDir = "/usr/"
            self.preferToUseShellInSubprocess = True
            binarySuffix = ""

        binBaseDir = os.path.join(baseDir, "bin")
        self.ssh = os.path.join(binBaseDir, "ssh" + binarySuffix)
        self.scp = os.path.join(binBaseDir, "scp" + binarySuffix)
        self.sshKeyGen = os.path.join(binBaseDir, "ssh-keygen" + binarySuffix)
        self.mkdir = os.path.join(binBaseDir, "mkdir" + binarySuffix)
        self.cat = os.path.join(binBaseDir, "cat" + binarySuffix)


class KeyPair(object):
    """
    Represents an SSH key-pair, e.g. (~/.ssh/MyData, ~/.ssh/MyData.pub)
    """
    def __init__(self, privateKeyFilePath, publicKeyFilePath):
        self.privateKeyFilePath = privateKeyFilePath
        self.publicKeyFilePath = publicKeyFilePath
        self.publicKey = None
        self.fingerprint = None
        self.keyType = None

    def GetPrivateKeyFilePath(self):
        return self.privateKeyFilePath

    def ReadPublicKey(self):
        """
        Read public key, including "ssh-rsa "
        """
        if self.publicKeyFilePath is not None and \
                os.path.exists(self.publicKeyFilePath):
            with open(self.publicKeyFilePath, "r") as pubKeyFile:
                return pubKeyFile.read()
        else:
            raise SshException("Couldn't access MyData.pub in ~/.ssh/")

    def Delete(self):
        try:
            os.unlink(self.privateKeyFilePath)
            if self.publicKeyFilePath is not None:
                os.unlink(self.publicKeyFilePath)
        except:
            logger.error(traceback.format_exc())
            return False

        return True

    def GetPublicKey(self):
        if self.publicKey is None:
            self.publicKey = self.ReadPublicKey()
        return self.publicKey

    def ReadFingerprintAndKeyType(self):
        """
        Use "ssh-keygen -yl -f privateKeyFile" to extract the fingerprint
        and key type.  This only works if the public key file exists.
        If the public key file doesn't exist, we will generate it from
        the private key file using "ssh-keygen -y -f privateKeyFile".

        On Windows, we're using OpenSSH 7.1p1, and since OpenSSH
        version 6.8, ssh-keygen requires -E md5 to get the fingerprint
        in the old MD5 Hexadecimal format.
        http://www.openssh.com/txt/release-6.8
        Eventually we could switch to the new format, but then MyTardis
        administrators would need to re-approve Uploader Registration
        Requests because of the fingerprint mismatches.
        See the UploaderModel class's ExistingUploadToStagingRequest
        method in mydata.models.uploader

        On Mac OS X, passing the entire command string (with arguments)
        to subprocess, rather than a list requires using "shell=True",
        otherwise Python will check whether the "file", e.g.
        "/usr/bin/ssh-keygen -yl -f ~/.ssh/MyData" exists
        which of course it doesn't.  Passing a command list on the
        other hand is problematic on Windows where Python's automatic
        quoting to convert the command list to a command doesn't always
        work as desired.
        """
        if not os.path.exists(self.privateKeyFilePath):
            raise PrivateKeyDoesNotExist("Couldn't find valid private key in "
                                         "%s" % self.privateKeyFilePath)
        if self.publicKeyFilePath is None:
            self.publicKeyFilePath = self.privateKeyFilePath + ".pub"
        if not os.path.exists(self.publicKeyFilePath):
            publicKey = self.GetPublicKey()
            with open(self.publicKeyFilePath, "w") as pubKeyFile:
                pubKeyFile.write(publicKey)

        if sys.platform.startswith('win'):
            quotedPrivateKeyFilePath = \
                OPENSSH.DoubleQuote(GetCygwinPath(self.privateKeyFilePath))
            cmdList = [OPENSSH.DoubleQuote(OPENSSH.sshKeyGen), "-E", "md5",
                       "-yl", "-f", quotedPrivateKeyFilePath]
        else:
            quotedPrivateKeyFilePath = \
                OPENSSH.DoubleQuote(self.privateKeyFilePath)
            cmdList = [OPENSSH.DoubleQuote(OPENSSH.sshKeyGen),
                       "-yl", "-f", quotedPrivateKeyFilePath]
        cmd = " ".join(cmdList)
        logger.debug(cmd)
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                universal_newlines=True,
                                shell=True,
                                startupinfo=DEFAULT_STARTUP_INFO,
                                creationflags=DEFAULT_CREATION_FLAGS)
        stdout, _ = proc.communicate()
        if proc.returncode != 0:
            raise SshException(stdout)

        fingerprint = None
        keyType = None
        if stdout is not None:
            sshKeyGenOutComponents = stdout.split(" ")
            if len(sshKeyGenOutComponents) > 1:
                fingerprint = sshKeyGenOutComponents[1]
                if fingerprint.upper().startswith("MD5:"):
                    fingerprint = fingerprint[4:]
            if len(sshKeyGenOutComponents) > 3:
                keyType = sshKeyGenOutComponents[-1]\
                    .strip().strip('(').strip(')')

        return fingerprint, keyType

    def GetFingerprint(self):
        if self.fingerprint is None:
            self.fingerprint, self.keyType = self.ReadFingerprintAndKeyType()
        return self.fingerprint

    def GetKeyType(self):
        if self.keyType is None:
            self.fingerprint, self.keyType = self.ReadFingerprintAndKeyType()
        return self.keyType


def FindKeyPair(keyName="MyData", keyPath=None):
    if keyPath is None:
        keyPath = os.path.join(os.path.expanduser('~'), ".ssh")
    if os.path.exists(os.path.join(keyPath, keyName)):
        with open(os.path.join(keyPath, keyName)) as keyFile:
            for line in keyFile:
                if re.search(r"BEGIN .* PRIVATE KEY", line):
                    privateKeyFilePath = os.path.join(keyPath, keyName)
                    publicKeyFilePath = os.path.join(keyPath, keyName + ".pub")
                    if not os.path.exists(publicKeyFilePath):
                        publicKeyFilePath = None
                    return KeyPair(privateKeyFilePath, publicKeyFilePath)
    raise PrivateKeyDoesNotExist("Couldn't find valid private key in %s"
                                 % os.path.join(keyPath, keyName))


def NewKeyPair(keyName=None, keyPath=None, keyComment=None):
    """
    Create an RSA key-pair in ~/.ssh for use with SSH and SCP.
    """
    if keyName is None:
        keyName = "MyData"
    if keyPath is None:
        keyPath = os.path.join(os.path.expanduser('~'), ".ssh")
    if keyComment is None:
        keyComment = "MyData Key"
    privateKeyFilePath = os.path.join(keyPath, keyName)
    publicKeyFilePath = privateKeyFilePath + ".pub"

    dotSshDir = os.path.join(os.path.expanduser('~'), ".ssh")
    if not os.path.exists(dotSshDir):
        os.makedirs(dotSshDir)

    if sys.platform.startswith('win'):
        quotedPrivateKeyFilePath = \
            OPENSSH.DoubleQuote(GetCygwinPath(privateKeyFilePath))
    else:
        quotedPrivateKeyFilePath = OPENSSH.DoubleQuote(privateKeyFilePath)
    cmdList = \
        [OPENSSH.DoubleQuote(OPENSSH.sshKeyGen),
         "-f", quotedPrivateKeyFilePath,
         "-N", '""',
         "-C", OPENSSH.DoubleQuote(keyComment)]
    cmd = " ".join(cmdList)
    logger.debug(cmd)
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=True,
                            startupinfo=DEFAULT_STARTUP_INFO,
                            creationflags=DEFAULT_CREATION_FLAGS)
    stdout, _ = proc.communicate()

    if stdout is None or str(stdout).strip() == "":
        raise SshException("Received unexpected EOF from ssh-keygen.")
    elif "Your identification has been saved" in stdout:
        return KeyPair(privateKeyFilePath, publicKeyFilePath)
    elif "already exists" in stdout:
        raise SshException("Private key file \"%s\" already exists."
                           % privateKeyFilePath)
    else:
        raise SshException(stdout)


# pylint: disable=too-many-locals
def SshServerIsReady(username, privateKeyFilePath,
                     host, port):
    if sys.platform.startswith("win"):
        privateKeyFilePath = GetCygwinPath(privateKeyFilePath)

    if sys.platform.startswith("win"):
        cmdAndArgs = [OPENSSH.DoubleQuote(OPENSSH.ssh),
                      "-p", str(port),
                      "-i", OPENSSH.DoubleQuote(privateKeyFilePath),
                      "-oPasswordAuthentication=no",
                      "-oNoHostAuthenticationForLocalhost=yes",
                      "-oStrictHostKeyChecking=no",
                      "-l", username,
                      host,
                      OPENSSH.DoubleQuote("echo Ready")]
    else:
        cmdAndArgs = [OPENSSH.DoubleQuote(OPENSSH.ssh),
                      "-p", str(port),
                      "-i", OPENSSH.DoubleQuote(privateKeyFilePath),
                      "-oPasswordAuthentication=no",
                      "-oNoHostAuthenticationForLocalhost=yes",
                      "-oStrictHostKeyChecking=no",
                      "-l", username,
                      host,
                      OPENSSH.DoubleQuote("echo Ready")]
    cmdString = " ".join(cmdAndArgs)
    logger.debug(cmdString)
    proc = subprocess.Popen(cmdString,
                            shell=OPENSSH.preferToUseShellInSubprocess,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            startupinfo=DEFAULT_STARTUP_INFO,
                            creationflags=DEFAULT_CREATION_FLAGS)
    stdout, _ = proc.communicate()
    returncode = proc.returncode
    if returncode != 0:
        logger.error(stdout)

    return returncode == 0


# pylint: disable=too-many-arguments
# pylint: disable=too-many-function-args
def UploadFile(filePath, fileSize, username, privateKeyFilePath,
               host, port, remoteFilePath, progressCallback,
               foldersController, uploadModel):
    """
    Upload a file to staging using SCP.

    Ignore bytes uploaded previously, because MyData is no longer
    chunking files, so with SCP, we will always upload the whole
    file.
    """
    bytesUploaded = long(0)
    progressCallback(bytesUploaded, fileSize, message="Uploading...")

    if sys.platform.startswith("win"):
        return UploadFileFromWindows(filePath, fileSize, username,
                                     privateKeyFilePath, host, port,
                                     remoteFilePath, progressCallback,
                                     foldersController, uploadModel)
    else:
        return UploadFileFromPosixSystem(filePath, fileSize, username,
                                         privateKeyFilePath, host, port,
                                         remoteFilePath, progressCallback,
                                         foldersController, uploadModel)


def MonitorProgress(foldersController, progressPollInterval, uploadModel,
                    fileSize, monitoringProgress, progressCallback):
    """
    Monitor progress via RESTful queries.
    """
    settingsModel = foldersController.settingsModel
    if foldersController.IsShuttingDown() or \
            (uploadModel.GetStatus() != UploadStatus.IN_PROGRESS and
             uploadModel.GetStatus() != UploadStatus.NOT_STARTED):
        return
    timer = threading.Timer(progressPollInterval, MonitorProgress,
                            args=[foldersController, progressPollInterval,
                                  uploadModel, fileSize, monitoringProgress,
                                  progressCallback])
    timer.start()
    if uploadModel.GetStatus() == UploadStatus.NOT_STARTED:
        return
    if monitoringProgress.isSet():
        return
    monitoringProgress.set()
    dfoId = uploadModel.GetDfoId()
    if dfoId is None:
        dataFileId = uploadModel.GetDataFileId()
        if dataFileId is not None:
            try:
                dataFile = \
                    DataFileModel.GetDataFileFromId(settingsModel,
                                                    dataFileId)
                dfoId = dataFile.GetReplicas()[0].GetId()
                uploadModel.SetDfoId(dfoId)
            except DoesNotExist:
                # If the DataFile ID reported in the location header
                # after POSTing to the API doesn't exist yet, don't
                # worry, just check again later.
                pass
            except IndexError:
                # If the dataFile.GetReplicas()[0] DFO doesn't exist yet,
                # don't worry, just check again later.
                pass
    if dfoId:
        try:
            bytesUploaded = \
                ReplicaModel.CountBytesUploadedToStaging(settingsModel,
                                                         dfoId)
            latestUpdateTime = datetime.now()
            # If this file already has a partial upload in staging,
            # progress and speed estimates can be misleading.
            uploadModel.SetLatestTime(latestUpdateTime)
            uploadModel.SetBytesUploaded(bytesUploaded)
            progressCallback(bytesUploaded, fileSize)
        except requests.exceptions.RequestException:
            timer.cancel()
        except MissingMyDataReplicaApiEndpoint:
            timer.cancel()
    monitoringProgress.clear()


def UploadFileFromPosixSystem(filePath, fileSize, username, privateKeyFilePath,
                              host, port, remoteFilePath, progressCallback,
                              foldersController, uploadModel):
    """
    Upload file using SCP.
    """
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    settingsModel = foldersController.settingsModel
    cipher = settingsModel.GetCipher()
    progressPollInterval = settingsModel.GetProgressPollInterval()
    monitoringProgress = threading.Event()
    uploadModel.SetStartTime(datetime.now())
    MonitorProgress(foldersController, progressPollInterval, uploadModel,
                    fileSize, monitoringProgress, progressCallback)
    remoteDir = os.path.dirname(remoteFilePath)
    quotedRemoteDir = OPENSSH.DoubleQuoteRemotePath(remoteDir)
    if remoteDir not in REMOTE_DIRS_CREATED:
        mkdirCmdAndArgs = \
            [OPENSSH.DoubleQuote(OPENSSH.ssh),
             "-p", port,
             "-n",
             "-c", cipher,
             "-i", OPENSSH.DoubleQuote(privateKeyFilePath),
             "-oPasswordAuthentication=no",
             "-oNoHostAuthenticationForLocalhost=yes",
             "-oStrictHostKeyChecking=no",
             "-l", username,
             host,
             OPENSSH.DoubleQuote("mkdir -p %s" % quotedRemoteDir)]
        mkdirCmdString = " ".join(mkdirCmdAndArgs)
        logger.debug(mkdirCmdString)
        if not sys.platform.startswith("linux"):
            mkdirProcess = \
                subprocess.Popen(mkdirCmdString,
                                 shell=OPENSSH.preferToUseShellInSubprocess,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 startupinfo=DEFAULT_STARTUP_INFO,
                                 creationflags=DEFAULT_CREATION_FLAGS)
            stdout, _ = mkdirProcess.communicate()
            if mkdirProcess.returncode != 0:
                raise SshException(stdout, mkdirProcess.returncode)
        else:
            stdout, stderr, returncode = \
                GetErrandBoyTransport().run_cmd(mkdirCmdString)
            if returncode != 0:
                raise SshException(stderr, returncode)
        REMOTE_DIRS_CREATED[remoteDir] = True

    if uploadModel.Canceled():
        logger.debug("UploadFileFromPosixSystem: Aborting upload "
                     "for %s" % filePath)
        return

    maxThreads = settingsModel.GetMaxUploadThreads()
    remoteDir = os.path.dirname(remoteFilePath)
    if settingsModel.UseNoneCipher():
        cipherString = "-oNoneEnabled=yes -oNoneSwitch=yes"
    else:
        cipherString = "-c %s" % cipher
    scpCommandString = \
        '%s -P %s -i %s %s ' \
        '-oPasswordAuthentication=no ' \
        '-oNoHostAuthenticationForLocalhost=yes ' \
        '-oStrictHostKeyChecking=no ' \
        '%s "%s@%s:\\"%s\\""' \
        % (OPENSSH.DoubleQuote(OPENSSH.scp),
           port,
           privateKeyFilePath,
           cipherString,
           OPENSSH.DoubleQuote(filePath),
           username, host,
           remoteDir
           .replace('`', r'\\`')
           .replace('$', r'\\$'))
    logger.debug(scpCommandString)
    if not sys.platform.startswith("linux"):
        scpUploadProcess = subprocess.Popen(
            scpCommandString,
            shell=OPENSSH.preferToUseShellInSubprocess,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        uploadModel.SetScpUploadProcessPid(scpUploadProcess.pid)
        while True:
            poll = scpUploadProcess.poll()
            if poll is not None:
                break
            time.sleep(SLEEP_FACTOR * maxThreads)
        stdout, _ = scpUploadProcess.communicate()
        returncode = scpUploadProcess.returncode
        if returncode != 0:
            raise ScpException(stdout, scpCommandString, returncode)
    else:
        with GetErrandBoyTransport().get_session() as session:
            ebSubprocess = session.subprocess
            if sys.platform.startswith("linux"):
                preexecFunction = os.setpgrp
            else:
                preexecFunction = None
            scpUploadProcess = \
                ebSubprocess.Popen(scpCommandString, shell=True,
                                   close_fds=True, preexec_fn=preexecFunction)
            uploadModel.SetStatus(UploadStatus.IN_PROGRESS)
            uploadModel.SetScpUploadProcessPid(scpUploadProcess.pid)

            while True:
                poll = scpUploadProcess.poll()
                if poll is not None:
                    break
                time.sleep(SLEEP_FACTOR * maxThreads)
            stdout, stderr = scpUploadProcess.communicate()
            returncode = scpUploadProcess.returncode

    latestUpdateTime = datetime.now()
    uploadModel.SetLatestTime(latestUpdateTime)
    if returncode != 0:
        raise ScpException(stdout, scpCommandString,
                           returncode)
    bytesUploaded = fileSize
    progressCallback(bytesUploaded, fileSize)
    return

REMOTE_DIRS_CREATED = dict()


def UploadFileFromWindows(filePath, fileSize, username,
                          privateKeyFilePath, host, port, remoteFilePath,
                          progressCallback, foldersController, uploadModel):
    """
    Upload file using SCP.
    """
    # pylint: disable=too-many-statements
    uploadModel.SetStartTime(datetime.now())
    settingsModel = foldersController.settingsModel
    maxThreads = settingsModel.GetMaxUploadThreads()
    progressPollInterval = settingsModel.GetProgressPollInterval()
    monitoringProgress = threading.Event()
    MonitorProgress(foldersController, progressPollInterval, uploadModel,
                    fileSize, monitoringProgress, progressCallback)
    cipher = settingsModel.GetCipher()
    remoteDir = os.path.dirname(remoteFilePath)
    quotedRemoteDir = OPENSSH.DoubleQuoteRemotePath(remoteDir)
    if remoteDir not in REMOTE_DIRS_CREATED:
        mkdirCmdAndArgs = \
            [OPENSSH.DoubleQuote(OPENSSH.ssh),
             "-p", port,
             "-n",
             "-c", cipher,
             "-i", OPENSSH.DoubleQuote(privateKeyFilePath),
             "-oPasswordAuthentication=no",
             "-oNoHostAuthenticationForLocalhost=yes",
             "-oStrictHostKeyChecking=no",
             "-l", username,
             host,
             OPENSSH.DoubleQuote("mkdir -p %s" % quotedRemoteDir)]
        mkdirCmdString = " ".join(mkdirCmdAndArgs)
        logger.debug(mkdirCmdString)
        mkdirProcess = \
            subprocess.Popen(mkdirCmdString,
                             shell=OPENSSH.preferToUseShellInSubprocess,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             startupinfo=DEFAULT_STARTUP_INFO,
                             creationflags=DEFAULT_CREATION_FLAGS)
        stdout, _ = mkdirProcess.communicate()
        if mkdirProcess.returncode != 0:
            raise SshException(stdout, mkdirProcess.returncode)
        REMOTE_DIRS_CREATED[remoteDir] = True

    if uploadModel.Canceled():
        logger.debug("UploadFileFromWindows: Aborting upload "
                     "for %s" % filePath)
        return

    remoteDir = os.path.dirname(remoteFilePath)
    scpCommandString = \
        '%s -v -P %s -i %s -c %s ' \
        '-oNoHostAuthenticationForLocalhost=yes ' \
        '-oPasswordAuthentication=no -oStrictHostKeyChecking=no ' \
        '%s "%s@%s:\\"%s/\\""' \
        % (OPENSSH.DoubleQuote(OPENSSH.scp), port,
           OPENSSH.DoubleQuote(GetCygwinPath(privateKeyFilePath)),
           cipher,
           OPENSSH.DoubleQuote(GetCygwinPath(filePath)),
           username, host,
           remoteDir
           .replace('`', r'\\`')
           .replace('$', r'\\$'))
    logger.debug(scpCommandString)
    scpUploadProcess = subprocess.Popen(
        scpCommandString,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        startupinfo=DEFAULT_STARTUP_INFO,
        creationflags=DEFAULT_CREATION_FLAGS)
    uploadModel.SetScpUploadProcessPid(scpUploadProcess.pid)
    uploadModel.SetStatus(UploadStatus.IN_PROGRESS)
    while True:
        poll = scpUploadProcess.poll()
        if poll is not None:
            break
        time.sleep(SLEEP_FACTOR * maxThreads)
    stdout, _ = scpUploadProcess.communicate()
    if scpUploadProcess.returncode != 0:
        raise ScpException(stdout, scpCommandString,
                           scpUploadProcess.returncode)
    bytesUploaded = fileSize
    progressCallback(bytesUploaded, fileSize)
    return


def GetCygwinPath(path):
    """
    Converts "C:\\path\\to\\file" to "/cygdrive/C/path/to/file".
    """
    realpath = os.path.realpath(path)
    match = re.search(r"^(\S):(.*)", realpath)
    if match:
        return "/cygdrive/" + match.groups()[0] + \
            match.groups()[1].replace("\\", "/")
    else:
        raise Exception("OpenSSH.GetCygwinPath: %s doesn't look like "
                        "a valid path." % path)


def CleanUpSshProcesses(settingsModel):
    """
    SCP can leave orphaned SSH processes which need to be cleaned up.
    On Windows, we bundle our own SSH binary with MyData, so we can
    check that the absolute path of the SSH executable to be terminated
    matches MyData's SSH path.  On other platforms, we can use proc.cmdline()
    to ensure that the SSH process we're killing uses MyData's private key.
    """
    privateKeyPath = settingsModel.GetSshKeyPair().GetPrivateKeyFilePath()
    for proc in psutil.process_iter():
        try:
            if proc.exe() == OPENSSH.ssh:
                try:
                    if privateKeyPath in proc.cmdline():
                        proc.kill()
                    elif sys.platform.startswith("win"):
                        proc.kill()
                except:
                    pass
        except psutil.AccessDenied:
            pass


# Singleton instance of OpenSSH class:
OPENSSH = OpenSSH()

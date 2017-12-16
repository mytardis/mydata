"""
Methods for using OpenSSH functionality from MyData.
On Windows, we bundle a Cygwin build of OpenSSH.
"""
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

from ..events.stop import ShouldCancelUpload
from ..settings import SETTINGS
from ..logs import logger
from ..models.upload import UploadStatus
from ..utils.exceptions import SshException
from ..utils.exceptions import ScpException
from ..utils.exceptions import PrivateKeyDoesNotExist
from ..threads.locks import LOCKS

from ..subprocesses import DEFAULT_STARTUP_INFO
from ..subprocesses import DEFAULT_CREATION_FLAGS

from .progress import MonitorProgress

if sys.platform.startswith("win"):
    import win32process

if sys.platform.startswith("linux"):
    import mydata.linuxsubprocesses as linuxsubprocesses

# Running subprocess's communicate from multiple threads can cause high CPU
# usage, so we poll each subprocess before running communicate, using a sleep
# interval of SLEEP_FACTOR * maxThreads.
SLEEP_FACTOR = 0.01

REMOTE_DIRS_CREATED = dict()


class OpenSSH(object):
    """
    A singleton instance of this class (called OPENSSH) is created in this
    module which contains paths to SSH binaries and quoting methods used for
    running remote commands over SSH via subprocesses.
    """
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
            winOpensshDir = r"win32\openssh-7.3p1-cygwin-2.8.0"
        if hasattr(sys, "frozen"):
            baseDir = os.path.dirname(sys.executable)
        else:
            baseDir = os.path.dirname(pkgutil.get_loader("mydata").filename)
            winOpensshDir = os.path.join("resources", winOpensshDir)
        if sys.platform.startswith("win"):
            baseDir = os.path.join(baseDir, winOpensshDir)
            binarySuffix = ".exe"
            dotSshDir = os.path.join(
                baseDir, "home", getpass.getuser(), ".ssh")
            if not os.path.exists(dotSshDir):
                os.makedirs(dotSshDir)
        else:
            baseDir = "/usr/"
            binarySuffix = ""

        binBaseDir = os.path.join(baseDir, "bin")
        self.ssh = os.path.join(binBaseDir, "ssh" + binarySuffix)
        self.scp = os.path.join(binBaseDir, "scp" + binarySuffix)
        self.sshKeyGen = os.path.join(binBaseDir, "ssh-keygen" + binarySuffix)
        self.mkdir = os.path.join(binBaseDir, "mkdir" + binarySuffix)
        self.cat = os.path.join(binBaseDir, "cat" + binarySuffix)

    @staticmethod
    def DoubleQuote(string):
        """
        Return double-quoted string
        """
        return '"' + string.replace('"', r'\"') + '"'

    @staticmethod
    def DoubleQuoteRemotePath(string):
        """
        Return double-quoted remote path, escaping double quotes,
        backticks and dollar signs
        """
        path = string.replace('"', r'\"')
        path = path.replace('`', r'\\`')
        path = path.replace('$', r'\\$')
        return '"%s"' % path

    @staticmethod
    def DefaultSshOptions(connectionTimeout):
        """
        Returns default SSH options
        """
        return [
            "-oPasswordAuthentication=no",
            "-oNoHostAuthenticationForLocalhost=yes",
            "-oStrictHostKeyChecking=no",
            "-oConnectTimeout=%s" % int(connectionTimeout)
        ]


class KeyPair(object):
    """
    Represents an SSH key-pair, e.g. (~/.ssh/MyData, ~/.ssh/MyData.pub)
    """
    def __init__(self, privateKeyFilePath, publicKeyFilePath):
        self.privateKeyFilePath = privateKeyFilePath
        self.publicKeyFilePath = publicKeyFilePath
        self._publicKey = None
        self._fingerprint = None
        self.keyType = None

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
        """
        Delete SSH keypair

        Only used by tests
        """
        try:
            os.unlink(self.privateKeyFilePath)
            if self.publicKeyFilePath is not None:
                os.unlink(self.publicKeyFilePath)
        except:
            logger.error(traceback.format_exc())
            return False

        return True

    @property
    def publicKey(self):
        """
        Return public key as string
        """
        if self._publicKey is None:
            self._publicKey = self.ReadPublicKey()
        return self._publicKey

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
        """
        if not os.path.exists(self.privateKeyFilePath):
            raise PrivateKeyDoesNotExist("Couldn't find valid private key in "
                                         "%s" % self.privateKeyFilePath)
        if self.publicKeyFilePath is None:
            self.publicKeyFilePath = self.privateKeyFilePath + ".pub"
        if not os.path.exists(self.publicKeyFilePath):
            with open(self.publicKeyFilePath, "w") as pubKeyFile:
                pubKeyFile.write(self.publicKey)

        if sys.platform.startswith('win'):
            cmdList = [OPENSSH.sshKeyGen, "-E", "md5",
                       "-yl", "-f", self.privateKeyFilePath]
        else:
            cmdList = [OPENSSH.sshKeyGen, "-yl", "-f", self.privateKeyFilePath]
        logger.debug(" ".join(cmdList))
        proc = subprocess.Popen(cmdList,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
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

    @property
    def fingerprint(self):
        """
        Return public key fingerprint
        """
        if self._fingerprint is None:
            self._fingerprint, self.keyType = self.ReadFingerprintAndKeyType()
        return self._fingerprint


def FindKeyPair(keyName="MyData", keyPath=None):
    """
    Find an SSH key pair
    """
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

    We use shell=True with subprocess to allow entering an empty
    passphrase into ssh-keygen.  Otherwise (at least on macOS),
    we get:
        "Saving key ""/Users/james/.ssh/MyData"" failed:
         passphrase is too short (minimum five characters)
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
            OpenSSH.DoubleQuote(GetCygwinPath(privateKeyFilePath))
    else:
        quotedPrivateKeyFilePath = OpenSSH.DoubleQuote(privateKeyFilePath)
    cmdList = \
        [OpenSSH.DoubleQuote(OPENSSH.sshKeyGen),
         "-f", quotedPrivateKeyFilePath,
         "-N", '""',
         "-C", OpenSSH.DoubleQuote(keyComment)]
    cmd = " ".join(cmdList)
    logger.debug(cmd)
    proc = subprocess.Popen(cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=True,  # Allows empty passphrase
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


def SshServerIsReady(username, privateKeyFilePath,
                     host, port):
    """
    Check if SSH server is ready
    """
    if sys.platform.startswith("win"):
        privateKeyFilePath = GetCygwinPath(privateKeyFilePath)

    cmdAndArgs = [
        OPENSSH.ssh,
        "-p", str(port),
        "-i", privateKeyFilePath,
        "-l", username,
        host,
        "echo Ready"
    ]
    cmdAndArgs[1:1] = OpenSSH.DefaultSshOptions(
        SETTINGS.miscellaneous.connectionTimeout)
    logger.debug(" ".join(cmdAndArgs))
    proc = subprocess.Popen(cmdAndArgs,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            startupinfo=DEFAULT_STARTUP_INFO,
                            creationflags=DEFAULT_CREATION_FLAGS)
    stdout, _ = proc.communicate()
    returncode = proc.returncode
    if returncode != 0:
        logger.error(stdout)

    return returncode == 0


def UploadFile(filePath, fileSize, username, privateKeyFilePath,
               host, port, remoteFilePath, progressCallback,
               uploadModel):
    """
    Upload a file to staging using SCP.

    Ignore bytes uploaded previously, because MyData is no longer
    chunking files, so with SCP, we will always upload the whole
    file.
    """
    if sys.platform.startswith("win"):
        filePath = GetCygwinPath(filePath)
        privateKeyFilePath = GetCygwinPath(privateKeyFilePath)

    progressCallback(current=0, total=fileSize, message="Uploading...")

    monitoringProgress = threading.Event()
    uploadModel.startTime = datetime.now()
    MonitorProgress(SETTINGS.miscellaneous.progressPollInterval, uploadModel,
                    fileSize, monitoringProgress, progressCallback)

    remoteDir = os.path.dirname(remoteFilePath)
    with LOCKS.createRemoteDir:
        CreateRemoteDir(remoteDir, username, privateKeyFilePath, host, port)

    if ShouldCancelUpload(uploadModel):
        logger.debug("UploadFile: Aborting upload for %s" % filePath)
        return

    scpCommandList = [
        OPENSSH.scp,
        "-v",
        "-P", port,
        "-i", privateKeyFilePath,
        filePath,
        "%s@%s:%s" % (username, host,
                      remoteDir
                      .replace('`', r'\\`')
                      .replace('$', r'\\$'))]
    scpCommandList[2:2] = SETTINGS.miscellaneous.cipherOptions
    scpCommandList[2:2] = OpenSSH.DefaultSshOptions(
        SETTINGS.miscellaneous.connectionTimeout)

    if not sys.platform.startswith("linux"):
        ScpUpload(uploadModel, scpCommandList)
    else:
        ScpUploadWithErrandBoy(uploadModel, scpCommandList)

    SetRemoteFilePermissions(
        remoteDir, username, privateKeyFilePath, host, port)

    uploadModel.SetLatestTime(datetime.now())
    progressCallback(current=fileSize, total=fileSize)


def ScpUpload(uploadModel, scpCommandList):
    """
    Perfom an SCP upload using subprocess.Popen
    """
    scpCommandString = " ".join(scpCommandList)
    logger.debug(scpCommandString)
    try:
        scpUploadProcess = subprocess.Popen(
            scpCommandList,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        uploadModel.scpUploadProcessPid = scpUploadProcess.pid
        WaitForProcessToComplete(scpUploadProcess)
        stdout, _ = scpUploadProcess.communicate()
        if scpUploadProcess.returncode != 0:
            raise ScpException(
                stdout, scpCommandString, scpUploadProcess.returncode)
    except (IOError, OSError) as err:
        raise ScpException(err, scpCommandString, returncode=255)


def ScpUploadWithErrandBoy(uploadModel, scpCommandList):
    """
    Perfom an SCP upload using Errand Boy (Linux only), which triggers
    a subprocess in a separate Python process via a Unix domain socket.

    https://github.com/greyside/errand-boy
    """
    scpCommandString = " ".join(scpCommandList)
    logger.debug(scpCommandString)
    with linuxsubprocesses.ERRAND_BOY_TRANSPORT.get_session() as session:
        try:
            scpUploadProcess = session.subprocess.Popen(
                scpCommandList, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, close_fds=True,
                preexec_fn=os.setpgrp)
            uploadModel.status = UploadStatus.IN_PROGRESS
            uploadModel.scpUploadProcessPid = scpUploadProcess.pid

            WaitForProcessToComplete(scpUploadProcess)
            stdout, stderr = scpUploadProcess.communicate()
            if scpUploadProcess.returncode != 0:
                if stdout and not stderr:
                    stderr = stdout
                raise ScpException(
                    stderr, scpCommandString, scpUploadProcess.returncode)
        except (IOError, OSError) as err:
            raise ScpException(err, scpCommandString, returncode=255)


def SetRemoteFilePermissions(remoteDir, username, privateKeyFilePath,
                             host, port):
    """
    Ensure that the mytardis account (via the mytardis group) has read and
    write access to the uploaded data so that it can be moved from staging into
    its permanent location.  With some older versions of OpenSSH (installed on
    the SCP server), umask settings from ~mydata/.bashrc are respected, but
    recent versions ignore ~/.bashrc, so we need to explicitly set the
    permissions.  rsync can do this (copy and set permissions) in a single
    command, so we could investigate switching from scp to rsync, but rsync is
    likely to be slower in most cases.

    The command we use to set the permissions is applied to all files in the
    remote directory - we avoid referring to a specific remote file path
    (including filename) where possible, because of potential quoting /
    escaping issues.  Given that we are running the chmod command for the
    entire remote directory, we could just run it once (after MyData has
    finished uploading files to that directory), however there's a risk that
    MyData will terminate before it has finished uploading a directory's files,
    so we run the chmod after each upload for now.
    """
    remotePath = "%s/*" % remoteDir.rstrip('/')
    chmodCmdAndArgs = \
        [OPENSSH.ssh,
         "-p", port,
         "-n",
         "-c", SETTINGS.miscellaneous.cipher,
         "-i", privateKeyFilePath,
         "-l", username,
         host,
         "chmod 660 %s" % remotePath]
    chmodCmdAndArgs[1:1] = OpenSSH.DefaultSshOptions(
        SETTINGS.miscellaneous.connectionTimeout)
    logger.debug(" ".join(chmodCmdAndArgs))
    if not sys.platform.startswith("linux"):
        chmodProcess = \
            subprocess.Popen(chmodCmdAndArgs,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             startupinfo=DEFAULT_STARTUP_INFO,
                             creationflags=DEFAULT_CREATION_FLAGS)
        stdout, _ = chmodProcess.communicate()
        if chmodProcess.returncode != 0:
            raise SshException(stdout, chmodProcess.returncode)
    else:
        with linuxsubprocesses.ERRAND_BOY_TRANSPORT.get_session() as session:
            try:
                chmodProcess = session.subprocess.Popen(
                    chmodCmdAndArgs, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, close_fds=True,
                    preexec_fn=os.setpgrp)
                stdout, stderr = chmodProcess.communicate()
                if chmodProcess.returncode != 0:
                    if stdout and not stderr:
                        stderr = stdout
                    raise SshException(stderr, chmodProcess.returncode)
            except (IOError, OSError) as err:
                raise SshException(err, returncode=255)


def SetRemoteDirPermissions(remoteDir, username, privateKeyFilePath,
                            host, port):
    """
    Ensure that the mytardis account (via the mytardis group) has read and
    write access to the uploaded data so that it can be moved from staging
    into its permanent location.  With some older versions of OpenSSH
    (installed on the SCP server), umask settings from ~mydata/.bashrc are
    respected, but recent versions ignore ~/.bashrc, so we need to explicitly
    set the permissions.

    The command we use to set the permissions on subdirectories we create
    with mkdir over ssh is "chmod 2770", where 2 sets the setgid bit, so all
    child subdirectories should be created with the parent directory's group
    ("mytardis") rather than the "mydata" group.
    """
    chmodCmdAndArgs = \
        [OPENSSH.ssh,
         "-p", port,
         "-n",
         "-c", SETTINGS.miscellaneous.cipher,
         "-i", privateKeyFilePath,
         "-l", username,
         host,
         "chmod 2770 %s" % remoteDir]
    chmodCmdAndArgs[1:1] = OpenSSH.DefaultSshOptions(
        SETTINGS.miscellaneous.connectionTimeout)
    logger.debug(" ".join(chmodCmdAndArgs))
    if not sys.platform.startswith("linux"):
        chmodProcess = \
            subprocess.Popen(chmodCmdAndArgs,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             startupinfo=DEFAULT_STARTUP_INFO,
                             creationflags=DEFAULT_CREATION_FLAGS)
        stdout, _ = chmodProcess.communicate()
        if chmodProcess.returncode != 0:
            raise SshException(stdout, chmodProcess.returncode)
    else:
        with linuxsubprocesses.ERRAND_BOY_TRANSPORT.get_session() as session:
            try:
                chmodProcess = session.subprocess.Popen(
                    chmodCmdAndArgs, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, close_fds=True,
                    preexec_fn=os.setpgrp)
                stdout, stderr = chmodProcess.communicate()
                if chmodProcess.returncode != 0:
                    if stdout and not stderr:
                        stderr = stdout
                    raise SshException(stderr, chmodProcess.returncode)
            except (IOError, OSError) as err:
                raise SshException(err, returncode=255)


def WaitForProcessToComplete(process):
    """
    subprocess's communicate should do this automatically,
    but sometimes it polls too aggressively, putting unnecessary
    strain on CPUs (especially when done from multiple threads).
    """
    while True:
        poll = process.poll()
        if poll is not None:
            break
        time.sleep(SLEEP_FACTOR * SETTINGS.advanced.maxUploadThreads)


def CreateRemoteDir(remoteDir, username, privateKeyFilePath, host, port):
    """
    Create a remote directory over SSH
    """
    if remoteDir not in REMOTE_DIRS_CREATED:
        mkdirCmdAndArgs = \
            [OPENSSH.ssh,
             "-p", port,
             "-n",
             "-c", SETTINGS.miscellaneous.cipher,
             "-i", privateKeyFilePath,
             "-l", username,
             host,
             "mkdir -p %s" % remoteDir]
        mkdirCmdAndArgs[1:1] = OpenSSH.DefaultSshOptions(
            SETTINGS.miscellaneous.connectionTimeout)
        logger.debug(" ".join(mkdirCmdAndArgs))
        if not sys.platform.startswith("linux"):
            mkdirProcess = \
                subprocess.Popen(mkdirCmdAndArgs,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 startupinfo=DEFAULT_STARTUP_INFO,
                                 creationflags=DEFAULT_CREATION_FLAGS)
            stdout, _ = mkdirProcess.communicate()
            if mkdirProcess.returncode != 0:
                raise SshException(stdout, mkdirProcess.returncode)
        else:
            with linuxsubprocesses.ERRAND_BOY_TRANSPORT.get_session() as session:
                try:
                    mkdirProcess = session.subprocess.Popen(
                        mkdirCmdAndArgs, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, close_fds=True,
                        preexec_fn=os.setpgrp)
                    stdout, stderr = mkdirProcess.communicate()
                    if mkdirProcess.returncode != 0:
                        if stdout and not stderr:
                            stderr = stdout
                        raise SshException(stderr, mkdirProcess.returncode)
                except (IOError, OSError) as err:
                    raise SshException(err, returncode=255)
        SetRemoteDirPermissions(
            remoteDir, username, privateKeyFilePath, host, port)
        REMOTE_DIRS_CREATED[remoteDir] = True

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


def CleanUpScpAndSshProcesses():
    """
    SCP can leave orphaned SSH processes which need to be cleaned up.
    On Windows, we bundle our own SSH binary with MyData, so we can
    check that the absolute path of the SSH executable to be terminated
    matches MyData's SSH path.  On other platforms, we can use proc.cmdline()
    to ensure that the SSH process we're killing uses MyData's private key.
    """
    if not SETTINGS.uploaderModel:
        return
    privateKeyPath = SETTINGS.uploaderModel.sshKeyPair.privateKeyFilePath
    for proc in psutil.process_iter():
        try:
            if proc.exe() == OPENSSH.ssh or proc.exe() == OPENSSH.scp:
                try:
                    if privateKeyPath in proc.cmdline() or \
                            sys.platform.startswith("win"):
                        proc.kill()
                except:
                    pass
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            pass


# Singleton instance of OpenSSH class:
OPENSSH = OpenSSH()

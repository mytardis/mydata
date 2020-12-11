"""
Methods for using OpenSSH functionality from MyData.
On Windows, we bundle a PowerShell build of OpenSSH.
https://github.com/PowerShell/Win32-OpenSSH/releases
"""
import sys
from datetime import datetime
import os
import subprocess
import re
import getpass
import threading
import time
import struct
import hashlib
import psutil

from ..events.stop import ShouldCancelUpload
from ..settings import SETTINGS
from ..logs import logger
from ..models.upload import UploadStatus
from ..utils.upload import UploadFileChunked, UploadFileSsh
from ..utils.exceptions import PrivateKeyDoesNotExist, SshException, ScpException, UploadFailed
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
SLEEP_FACTOR = 0.1


class OpenSSH(object):
    """
    A singleton instance of this class (called OPENSSH) is created in this
    module which contains paths to SSH binaries and quoting methods used for
    running remote commands over SSH via subprocesses.
    """
    def __init__(self):
        self.cache = {}
        if "HOME" not in os.environ:
            os.environ["HOME"] = os.path.expanduser('~')

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


def NormalizeLocalPath(filePath):
    """
    Use Unix-style paths for Windows
    """
    if sys.platform.startswith("win"):
        return filePath.replace("\\", "/")
    return OpenSSH.DoubleQuote(filePath)


def WithDefaultOptions(opts, args):
    """
    Returns command with default SSH options
    """
    isSSH = isinstance(opts, list)

    cmdWithArgs = [
        GetOpenSshBinary("ssh") if isSSH else GetOpenSshBinary(opts),
        "-oPasswordAuthentication=no",
        "-oNoHostAuthenticationForLocalhost=yes",
        "-oStrictHostKeyChecking=no",
        "-oConnectTimeout=%s" % int(SETTINGS.miscellaneous.connectionTimeout),
        "-c", SETTINGS.miscellaneous.cipher
    ]

    if isSSH:
        cmdWithArgs += [
            "-p", opts[1],  # port
            "-l", opts[2],  # username
            "-i", opts[3],  # keyfile
            opts[0]         # host
        ]

    cmdWithArgs += args

    logger.debug(" ".join(cmdWithArgs))

    return cmdWithArgs


def GetOpenSshBinary(cmd, method=None):
    """
    Locate the SSH binaries on various systems.
    """
    x64 = (struct.calcsize('P') * 8 == 64) or \
          (sys.platform.startswith("win") and win32process.IsWow64Process())

    if method is None:
        method = SETTINGS.advanced.uploadMethod

    if hasattr(sys, "frozen"):
        baseDir = os.path.dirname(sys.executable)
    else:
        baseDir = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        baseDir = os.path.join(baseDir, "resources")

    if sys.platform.startswith("win"):
        if "OpenSSH" in method:
            if "8.1" in method:
                winDir = "openssh-8.1.0.0p1-beta"
            elif "7.9" in method:
                winDir = "openssh-7.9.0.0p1-beta"
            else:
                return GetOpenSshBinary(cmd, "OpenSSH 8.1")
            baseDir = os.path.join(
                baseDir,
                "win{}".format("64" if x64 else "32"),
                winDir)
            binarySuffix = ".exe"
        else:
            return GetOpenSshBinary(cmd, "OpenSSH 8.1")
    else:
        baseDir = "/usr/bin/"
        binarySuffix = ""

    return os.path.join(baseDir, cmd + binarySuffix)


def RunOpenSshCommand(cmd, raiseOnError=True, returnSuccess=False):
    """
    Run OpenSSH command
    """
    if not sys.platform.startswith("linux"):
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=os.path.dirname(cmd[0]),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
    else:
        with linuxsubprocesses.ERRAND_BOY_TRANSPORT.get_session() as session:
            try:
                proc = session.subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    close_fds=True,
                    preexec_fn=os.setpgrp)
            except (IOError, OSError) as err:
                raise SshException(err, returncode=255)

    stdout, _ = proc.communicate()
    details = stdout.decode()

    if proc.returncode != 0:
        logger.error(details)
        if raiseOnError:
            raise SshException(details, proc.returncode)

    if returnSuccess:
        return proc.returncode == 0

    return proc.returncode, details


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
        os.remove(self.privateKeyFilePath)
        if self.publicKeyFilePath is not None:
            os.remove(self.publicKeyFilePath)

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
            cmdList = [
                GetOpenSshBinary("ssh-keygen"),
                "-E", "md5",
                "-yl",
                "-f", self.privateKeyFilePath
            ]
        else:
            cmdList = [
                GetOpenSshBinary("ssh-keygen"),
                "-yl",
                "-f", self.privateKeyFilePath
        ]
        logger.debug(" ".join(cmdList))
        proc = subprocess.Popen(
            cmdList,
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
            sshKeyGenOutComponents = stdout.split(b" ")
            if len(sshKeyGenOutComponents) > 1:
                fingerprint = sshKeyGenOutComponents[1]
                if fingerprint.upper().startswith(b"MD5:"):
                    fingerprint = fingerprint[4:]
            if len(sshKeyGenOutComponents) > 3:
                keyType = sshKeyGenOutComponents[-1]\
                    .strip().strip(b'(').strip(b')')

        return fingerprint.decode(), keyType.decode()

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
    if not keyPath:
        keyPath = GetKeyPairLocation()
    if os.path.exists(os.path.join(keyPath, keyName)):
        with open(os.path.join(keyPath, keyName)) as keyFile:
            for line in keyFile:
                if re.search(r"BEGIN .* PRIVATE KEY", line):
                    privateKeyFilePath = os.path.join(keyPath, keyName)
                    publicKeyFilePath = os.path.join(keyPath, keyName + ".pub")
                    if not os.path.exists(publicKeyFilePath):
                        publicKeyFilePath = None
                    return KeyPair(privateKeyFilePath, publicKeyFilePath)
    return None


def NewKeyPair(keyName=None, keyPath=None, keyComment=None):
    """
    Create an RSA key-pair in ~/.ssh/ (or in keyPath if specified)
    for use with SSH and SCP.

    We use shell=True with subprocess to allow entering an empty
    passphrase into ssh-keygen.  Otherwise (at least on macOS),
    we get:
        "Saving key ""/Users/james/.ssh/MyData"" failed:
         passphrase is too short (minimum five characters)
    """
    if keyName is None:
        keyName = "MyData"
    if keyComment is None:
        keyComment = "MyData Key"
    if keyPath is None:
        keyPath = GetKeyPairLocation()
    if not os.path.exists(keyPath):
        os.makedirs(keyPath)

    privateKeyFilePath = os.path.join(keyPath, keyName)
    publicKeyFilePath = privateKeyFilePath + ".pub"

    code, message = RunOpenSshCommand([
        GetOpenSshBinary("ssh-keygen"),
        "-f", NormalizeLocalPath(privateKeyFilePath),
        "-N", '""',
        "-C", OpenSSH.DoubleQuote(keyComment)
    ], False)

    if message is None or len(message) == 0:
        raise SshException("Received unexpected EOF from ssh-keygen.")
    if "Your identification has been saved" in message:
        return KeyPair(privateKeyFilePath, publicKeyFilePath)
    if "already exists" in message:
        raise SshException("Private key file \"%s\" already exists." % privateKeyFilePath)

    raise SshException(message, code)


def GetKeyPairLocation():
    r"""
    Get a suitable location for the SSH key pair.

    On Windows (on which MyData is most commonly deployed), MyData uses
    a shared config directory of C:\ProgramData\Monash University\MyData\,
    shared amongst multiple Windows users, so it makes sense to store
    MyData's SSH key-pair in this central location.  This means that the
    private key is private to the instrument PC, but not private to an
    individual user of the instrument PC.
    """
    if sys.platform.startswith("win"):
        return os.path.join(
            os.path.dirname(SETTINGS.configPath), ".ssh")
    return os.path.join(os.path.expanduser('~'), ".ssh")


def FindOrCreateKeyPair(keyName="MyData"):
    r"""
    Find the MyData SSH key-pair, creating it if necessary
    """
    keyPath = GetKeyPairLocation()
    keyPair = FindKeyPair(keyName=keyName, keyPath=keyPath)
    if not keyPair and sys.platform.startswith("win"):
        # Didn't find private key in shared config location,
        # so look in traditional ~/.ssh/ location:
        keyPair = FindKeyPair(keyName=keyName)
    if not keyPair:
        keyPair = NewKeyPair(
            keyName=keyName, keyPath=keyPath,
            keyComment="%s@%s"
            % (getpass.getuser(), SETTINGS.general.instrumentName))
    return keyPair


def SshServerIsReady(ssh):
    """
    Check if SSH server is ready
    """
    return RunOpenSshCommand(
        WithDefaultOptions(
            ssh, [
                "echo Ready"
            ]),
        False,
        True)


def UploadFile(filePath, fileSize, username, privateKeyFilePath,
               host, port, remoteFilePath, progressCallback,
               uploadModel):
    """
    Upload a file to staging using SCP.

    Ignore bytes uploaded previously, because MyData is no longer
    chunking files, so with SCP, we will always upload the whole
    file.
    """
    ssh = [host, port, username, NormalizeLocalPath(privateKeyFilePath)]

    remoteDir = os.path.dirname(remoteFilePath)
    remoteDir = remoteDir.replace('`', r'\\`').replace('$', r'\\$')

    if SETTINGS.advanced.uploadMethod != "Chunked":
        cacheKey = hashlib.md5(remoteDir.encode("utf-8")).hexdigest()
        if cacheKey not in OPENSSH.cache:
            with LOCKS.createRemoteDir:
                CreateRemoteDir(ssh, remoteDir)
                OPENSSH.cache[cacheKey] = True

    if ShouldCancelUpload(uploadModel):
        logger.debug("UploadFile: Aborting upload for %s" % filePath)
        return

    progressCallback(current=0, total=fileSize, message="Uploading...")

    if SETTINGS.advanced.uploadMethod == "Chunked":

        try:
            UploadFileChunked(
                SETTINGS.general.myTardisUrl,
                SETTINGS.general.username,
                SETTINGS.general.apiKey,
                filePath,
                uploadModel,
                progressCallback)
        except Exception as err:
            raise UploadFailed(err)

    elif SETTINGS.advanced.uploadMethod == "ParallelSSH":

        try:
            UploadFileSsh(
                (host, int(port)),
                (username, privateKeyFilePath),
                filePath,
                remoteFilePath,
                uploadModel,
                progressCallback)
        except Exception as err:
            raise UploadFailed(err)

    else:

        monitoringProgress = threading.Event()
        uploadModel.startTime = datetime.now()
        MonitorProgress(SETTINGS.miscellaneous.progressPollInterval, uploadModel,
                        fileSize, monitoringProgress, progressCallback)

        scpCommandList = WithDefaultOptions(
            "scp", [
                "-P", port,
                "-i", NormalizeLocalPath(privateKeyFilePath),
                NormalizeLocalPath(filePath),
                "%s@%s:%s/" % (username, host, remoteDir)
            ])

        if not sys.platform.startswith("linux"):
            ScpUpload(uploadModel, scpCommandList)
        else:
            ScpUploadWithErrandBoy(uploadModel, scpCommandList)

    if SETTINGS.advanced.uploadMethod != "Chunked":
        SetRemoteFilePermissions(ssh, remoteFilePath)

    uploadModel.SetLatestTime(datetime.now())
    progressCallback(current=fileSize, total=fileSize)


def ScpUpload(uploadModel, cmd):
    """
    Perform an SCP upload using subprocess
    """
    scpCommandString = " ".join(cmd)
    logger.debug(scpCommandString)
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=os.path.dirname(cmd[0]),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        uploadModel.status = UploadStatus.IN_PROGRESS
        uploadModel.scpUploadProcessPid = proc.pid
        WaitForProcessToComplete(proc)
        stdout, _ = proc.communicate()
        if proc.returncode != 0:
            raise ScpException(
                stdout, scpCommandString, proc.returncode)
    except (IOError, OSError) as err:
        raise ScpException(err, scpCommandString, returncode=255)


def ScpUploadWithErrandBoy(uploadModel, scpCommandList):
    """
    Perform an SCP upload using Errand Boy (Linux only), which triggers
    a subprocess in a separate Python process via a Unix domain socket.

    https://github.com/greyside/errand-boy
    """
    scpCommandString = " ".join(scpCommandList)
    logger.debug(scpCommandString)
    with linuxsubprocesses.ERRAND_BOY_TRANSPORT.get_session() as session:
        try:
            scpUploadProcess = session.subprocess.Popen(
                scpCommandList,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
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


def CreateRemoteDir(ssh, remoteDir):
    """
    Create a remote directory via SSH
    """
    RunOpenSshCommand(
        WithDefaultOptions(
            ssh, [
                "mkdir -m 2770 -p %s" % OPENSSH.DoubleQuoteRemotePath(remoteDir)
            ]))


def SetRemoteFilePermissions(ssh, remoteFilePath):
    """
    Set file permissions via SSH
    """
    RunOpenSshCommand(
        WithDefaultOptions(
            ssh, [
                "chmod 660 %s" % OpenSSH.DoubleQuoteRemotePath(remoteFilePath)
            ]))


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
    try:
        privateKeyPath = SETTINGS.uploaderModel.sshKeyPair.privateKeyFilePath
    except AttributeError:
        # If sshKeyPair or privateKeyFilePath hasn't been defined yet,
        # then there won't be any SCP or SSH processes to kill.
        return
    for proc in psutil.process_iter():
        try:
            if proc.exe() == GetOpenSshBinary("ssh") or proc.exe() == GetOpenSshBinary("scp"):
                try:
                    if privateKeyPath in proc.cmdline() or sys.platform.startswith("win"):
                        proc.kill()
                except:
                    pass
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            pass


# Singleton instance of OpenSSH class:
OPENSSH = OpenSSH()

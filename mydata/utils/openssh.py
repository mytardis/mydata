"""
Methods for using OpenSSH functionality from MyData.
On Windows, we bundle a Cygwin build of OpenSSH.

subprocess is used extensively throughout this module.

Given the complex quoting requirements when running commands like
ssh staging_host "cat file.chunk >> file", I don't trust Python's
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
# pylint: disable=fixme
# pylint: disable=too-many-lines
# pylint: disable=wrong-import-position

import sys
import os
import subprocess
import traceback
import re
import tempfile
import getpass
import threading
import time
import pkgutil

if sys.platform.startswith("win"):
    # pylint: disable=import-error
    import win32process

from mydata.logs import logger
from mydata.utils.exceptions import SshException
from mydata.utils.exceptions import ScpException
from mydata.utils.exceptions import StagingHostRefusedSshConnection
from mydata.utils.exceptions import StagingHostSshPermissionDenied
from mydata.utils.exceptions import SshControlMasterLimit
from mydata.utils.exceptions import PrivateKeyDoesNotExist
from mydata.utils import PidIsRunning
from mydata.utils import HumanReadableSizeString


DEFAULT_STARTUP_INFO = None
DEFAULT_CREATION_FLAGS = 0
if sys.platform.startswith("win"):
    DEFAULT_STARTUP_INFO = subprocess.STARTUPINFO()
    # pylint: disable=protected-access
    DEFAULT_STARTUP_INFO.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
    DEFAULT_STARTUP_INFO.wShowWindow = subprocess.SW_HIDE
    DEFAULT_CREATION_FLAGS = win32process.CREATE_NO_WINDOW  # pylint: disable=no-member

# Running subprocess's communicate from multiple threads can cause high CPU
# usage, so we poll each subprocess before running communicate, using a sleep
# interval of SLEEP_FACTOR * maxThreads.
SLEEP_FACTOR = 0.01

# pylint: disable=too-many-instance-attributes
class OpenSSH(object):
    if hasattr(sys, "frozen"):
        opensshBuildDir = "openssh-7.1p1-cygwin-2.2.1"
    else:
        opensshBuildDir = "resources/win32/openssh-7.1p1-cygwin-2.2.1"

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
        if sys.platform.startswith("win"):
            if "HOME" not in os.environ:
                os.environ["HOME"] = os.path.expanduser('~')

        if sys.platform.startswith("win"):
            if hasattr(sys, "frozen"):
                baseDir = os.path.dirname(sys.executable)
            else:
                try:
                    baseDir = \
                        os.path.dirname(pkgutil.get_loader("mydata").filename)
                except:  # pylint: disable=bare-except
                    baseDir = os.getcwd()
            self.ssh = os.path.join(baseDir, self.opensshBuildDir,
                                    "bin", "ssh.exe")
            self.scp = os.path.join(baseDir, self.opensshBuildDir,
                                    "bin", "scp.exe")
            self.sshKeyGen = os.path.join(baseDir, self.opensshBuildDir,
                                          "bin", "ssh-keygen.exe")
            # The following binaries are only used for testing:
            self.mkdir = os.path.join(baseDir, self.opensshBuildDir,
                                      "bin", "mkdir.exe")
            self.cat = os.path.join(baseDir, self.opensshBuildDir,
                                    "bin", "cat.exe")
            # pylint: disable=invalid-name
            self.rm = os.path.join(baseDir, self.opensshBuildDir,
                                   "bin", "rm.exe")

            self.cipher = "arcfour128"
            self.preferToUseShellInSubprocess = False

            # This is not where we store the MyData private key.
            # This is where the Cygwin SSH build looks for our
            # known_hosts file.
            dotSshDir = os.path.join(self.opensshBuildDir,
                                     "home",
                                     getpass.getuser(),
                                     ".ssh")
            if not os.path.exists(dotSshDir):
                os.makedirs(dotSshDir)

        elif sys.platform.startswith("darwin"):
            self.ssh = "/usr/bin/ssh"
            self.scp = "/usr/bin/scp"
            self.sshKeyGen = "/usr/bin/ssh-keygen"
            self.cipher = "arcfour128"
            self.ddCmd = "/bin/dd"
            # False would be better below, but then (on POSIX
            # systems), I'd have to use command lists, instead
            # of command strings, and in some cases, I don't trust
            # subprocess to quote the command lists correctly.
            self.preferToUseShellInSubprocess = True
        else:
            self.ssh = "/usr/bin/ssh"
            self.scp = "/usr/bin/scp"
            self.sshKeyGen = "/usr/bin/ssh-keygen"
            self.cipher = "arcfour128"
            self.ddCmd = "/bin/dd"
            # False would be better below, but then (on POSIX
            # systems), I'd have to use command lists, instead
            # of command strings, and in some cases, I don't trust
            # subprocess to quote the command lists correctly.
            self.preferToUseShellInSubprocess = True

        # Only useful on POSIX systems:
        self.sshControlMasterPool = None
        self.createMasterPoolThreadingLock = threading.Lock()

    def GetSshControlMasterPool(self, username=None, privateKeyFilePath=None,
                                host=None, port=None, createIfMissing=True):
        """
        -oControlMaster is only available in POSIX implementations of ssh.
        """
        # pylint: disable=too-many-arguments
        if sys.platform.startswith("win"):
            raise NotImplementedError("-oControlMaster is not implemented "
                                      "in MinGW or Cygwin builds of OpenSSH.")
        if not self.sshControlMasterPool:
            if createIfMissing:
                self.createMasterPoolThreadingLock.acquire()
                self.sshControlMasterPool = \
                    SshControlMasterPool(username, privateKeyFilePath,
                                         host, port)
                self.createMasterPoolThreadingLock.release()
            else:
                return None
        return self.sshControlMasterPool


class KeyPair(object):

    def __init__(self, privateKeyFilePath, publicKeyFilePath):
        self.privateKeyFilePath = privateKeyFilePath
        self.publicKeyFilePath = publicKeyFilePath
        self.publicKey = None
        self.fingerprint = None
        self.keyType = None

    def __str__(self):
        return "KeyPair: " + \
            str({"privateKeyFilePath": self.privateKeyFilePath,
                 "publicKeyFilePath": self.publicKeyFilePath})

    def __repr__(self):
        return self.__str__()

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
        elif os.path.exists(self.privateKeyFilePath):
            cmdList = [OPENSSH.DoubleQuote(OPENSSH.sshKeyGen),
                       "-y",
                       "-f", OPENSSH.DoubleQuote(
                           GetCygwinPath(self.privateKeyFilePath))]
            cmd = " ".join(cmdList)
            logger.debug(cmd)
            proc = subprocess.Popen(cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True,
                                    startupinfo=DEFAULT_STARTUP_INFO,
                                    creationflags=DEFAULT_CREATION_FLAGS)
            stdout, _ = proc.communicate()

            if proc.returncode != 0:
                raise SshException(stdout)

            return stdout
        else:
            raise SshException("Couldn't find MyData key files in ~/.ssh "
                               "while trying to read public key.")

    def Delete(self):
        # pylint: disable=bare-except
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
            # On Windows, we're using OpenSSH 7.1p1, and since OpenSSH
            # version 6.8, ssh-keygen requires -E md5 to get the fingerprint
            # in the old MD5 Hexadecimal format.
            # http://www.openssh.com/txt/release-6.8
            # Eventually we could switch to the new format, but then MyTardis
            # administrators would need to re-approve Uploader Registration
            # Requests because of the fingerprint mismatches.
            # See the UploaderModel class's ExistingUploadToStagingRequest
            # method in mydata.models.uploader
            cmdList = [OPENSSH.DoubleQuote(OPENSSH.sshKeyGen), "-E", "md5",
                       "-yl", "-f", quotedPrivateKeyFilePath]
        else:
            quotedPrivateKeyFilePath = \
                OPENSSH.DoubleQuote(self.privateKeyFilePath)
            cmdList = [OPENSSH.DoubleQuote(OPENSSH.sshKeyGen),
                       "-yl", "-f", quotedPrivateKeyFilePath]
        cmd = " ".join(cmdList)
        logger.debug(cmd)
        # On Mac OS X, passing the entire command string (with arguments)
        # to subprocess, rather than a list requires using "shell=True",
        # otherwise Python will check whether the "file", e.g.
        # "/usr/bin/ssh-keygen -yl -f ~/.ssh/MyData" exists
        # which of course it doesn't.  Passing a command list on the
        # other hand is problematic on Windows where Python's automatic
        # quoting to convert the command list to a command doesn't always
        # work as desired.
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

        return (fingerprint, keyType)

    def GetFingerprint(self):
        if self.fingerprint is None:
            self.fingerprint, self.keyType = self.ReadFingerprintAndKeyType()
        return self.fingerprint

    def GetKeyType(self):
        if self.keyType is None:
            self.fingerprint, self.keyType = self.ReadFingerprintAndKeyType()
        return self.keyType


def ListKeyPairs(keyPath=None):
    if keyPath is None:
        keyPath = os.path.join(os.path.expanduser('~'), ".ssh")
    filesInKeyPath = [f for f in os.listdir(keyPath)
                      if os.path.isfile(os.path.join(keyPath, f))]
    keyPairs = []
    for potentialKeyFile in filesInKeyPath:
        with open(os.path.join(keyPath, potentialKeyFile)) as keyFile:
            for line in keyFile:
                if re.search(r"BEGIN .* PRIVATE KEY", line):
                    privateKeyFilePath = os.path.join(keyPath,
                                                      potentialKeyFile)
                    publicKeyFilePath = os.path.join(keyPath,
                                                     potentialKeyFile + ".pub")
                    if not os.path.exists(publicKeyFilePath):
                        publicKeyFilePath = None
                    keyPairs.append(KeyPair(privateKeyFilePath,
                                            publicKeyFilePath))
                    break
    return keyPairs


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
                      "-oIdentitiesOnly=yes",
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
                      "-oIdentitiesOnly=yes",
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
    if proc.returncode != 0:
        logger.debug(stdout)
    return proc.returncode == 0


def GetBytesUploadedToStaging(remoteFilePath, username, privateKeyFilePath,
                              host, port, settingsModel):
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    if sys.platform.startswith("win"):
        privateKeyFilePath = GetCygwinPath(privateKeyFilePath)
    quotedRemoteFilePath = OPENSSH.DoubleQuoteRemotePath(remoteFilePath)
    maxThreads = settingsModel.GetMaxVerificationThreads() + \
        settingsModel.GetMaxUploadThreads()

    if sys.platform.startswith("win"):
        cmdAndArgs = [OPENSSH.DoubleQuote(OPENSSH.ssh),
                      "-p", port,
                      "-n",
                      "-c", OPENSSH.cipher,
                      "-i", OPENSSH.DoubleQuote(privateKeyFilePath),
                      "-oIdentitiesOnly=yes",
                      "-oPasswordAuthentication=no",
                      "-oNoHostAuthenticationForLocalhost=yes",
                      "-oStrictHostKeyChecking=no",
                      "-l", username,
                      host,
                      OPENSSH.DoubleQuoteRemotePath(
                          "wc -c %s" % quotedRemoteFilePath)]
    else:
        if settingsModel.UseSshControlMasterIfAvailable():
            sshControlMasterPool = \
                OPENSSH.GetSshControlMasterPool(username, privateKeyFilePath,
                                                host, port)
            sshControlMasterProcess = \
                sshControlMasterPool.GetSshControlMasterProcess(maxThreads)
            sshControlPathOptionValuePair = \
                sshControlMasterProcess.GetControlPathOptionValuePair()
        else:
            sshControlPathOptionValuePair = ""

        # The authentication options below (-i privateKeyFilePath etc.)
        # shouldn't be necessary if the socket created by the SSH master
        # process (sshControlPath) is ready), but we can't guarantee that
        # it will be ready immediately.
        cmdAndArgs = [OPENSSH.DoubleQuote(OPENSSH.ssh),
                      "-p", port,
                      "-c", OPENSSH.cipher,
                      "-i", OPENSSH.DoubleQuote(privateKeyFilePath),
                      "-oIdentitiesOnly=yes",
                      "-oPasswordAuthentication=no",
                      "-oNoHostAuthenticationForLocalhost=yes",
                      "-oStrictHostKeyChecking=no",
                      "-l", username,
                      sshControlPathOptionValuePair,
                      host,
                      OPENSSH.DoubleQuoteRemotePath(
                          "wc -c %s" % quotedRemoteFilePath)]
    cmdString = " ".join(cmdAndArgs)
    logger.debug(cmdString)
    proc = subprocess.Popen(cmdString,
                            shell=OPENSSH.preferToUseShellInSubprocess,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            startupinfo=DEFAULT_STARTUP_INFO,
                            creationflags=DEFAULT_CREATION_FLAGS)
    while True:
        poll = proc.poll()
        if poll is not None:
            break
        time.sleep(SLEEP_FACTOR * maxThreads)
    stdout, _ = proc.communicate()
    lines = stdout.splitlines()
    bytesUploaded = long(0)
    for line in lines:
        match = re.search(r"^(\d+)\s+\S+", line)
        if match:
            bytesUploaded = long(match.groups()[0])
            return bytesUploaded
        elif "No such file or directory" in line:
            bytesUploaded = long(0)
            return bytesUploaded
        elif line == "ssh_exchange_identification: read: " \
                "Connection reset by peer" or \
                line == "ssh_exchange_identification: " \
                        "Connection closed by remote host":
            message = "The MyTardis staging host assigned to your " \
                "MyData instance (%s) refused MyData's attempted " \
                "SSH connection." \
                "\n\n" \
                "There are a few possible reasons why this could occur." \
                "\n\n" \
                "1. Your MyTardis administrator could have forgotten to " \
                "grant your IP address access to MyTardis's staging " \
                "host, or" \
                "\n\n" \
                "2. Your IP address could have changed sinced you were " \
                "granted access to MyTardis's staging host, or" \
                "\n\n" \
                "3. MyData's attempts to log in to MyTardis's staging host " \
                "could have been flagged as suspicious, and your IP " \
                "address could have been temporarily banned." \
                "\n\n" \
                "4. MyData could be running more simultaneous upload " \
                "threads than your staging server can handle.  Ask your " \
                "server administrator to check the values of MaxStartups " \
                "and MaxSessions in the server's /etc/ssh/sshd_config" \
                "\n\n" \
                "In any of these cases, it is best to contact your " \
                "MyTardis administrator for assistance." % host
            logger.error(stdout)
            logger.error(message)
            raise StagingHostRefusedSshConnection(message)
        elif line == "Permission denied (publickey,password).":
            message = "MyData was unable to authenticate into the " \
                "MyTardis staging host assigned to your MyData instance " \
                "(%s)." \
                "\n\n" \
                "There are a few possible reasons why this could occur." \
                "\n\n" \
                "1. Your MyTardis administrator could have failed to add " \
                "the public key generated by your MyData instance to the " \
                "appropriate ~/.ssh/authorized_keys file on MyTardis's " \
                "staging host, or" \
                "\n\n" \
                "2. The private key generated by MyData (a file called " \
                "\"MyData\" in the \".ssh\" folder within your " \
                "user home folder (%s) could have been deleted or moved." \
                "\n\n" \
                "3. The permissions on %s could be too open - only the " \
                "current user account should be able to access this private " \
                "key file." \
                "\n\n" \
                "In any of these cases, it is best to contact your " \
                "MyTardis administrator for assistance." \
                % (host, os.path.expanduser("~"),
                   os.path.join(os.path.expanduser("~"), ".ssh",
                                "MyData"))

            logger.error(message)
            raise StagingHostSshPermissionDenied(message)
        else:
            logger.debug(line)
    return bytesUploaded


# pylint: disable=too-many-arguments
# pylint: disable=too-many-function-args
def UploadFile(filePath, fileSize, username, privateKeyFilePath,
               host, port, remoteFilePath, progressCallback,
               foldersController, uploadModel):
    """
    The file may have already been uploaded, so let's check
    for it (and check its size) on the server. We don't use
    checksums here because they are slow for large files,
    and ultimately it will be the MyTardis verification
    task which does the final check.
    """

    bytesUploaded = long(0)
    largeFileSize = 10 * 1024 * 1024  # FIXME: Magic number

    if fileSize > largeFileSize:
        progressCallback(bytesUploaded, fileSize,
                         message="Checking for a previous partial upload...")
        if uploadModel.GetBytesUploadedToStaging() is not None:
            bytesUploaded = uploadModel.GetBytesUploadedToStaging()
        else:
            settingsModel = foldersController.settingsModel
            bytesUploaded = GetBytesUploadedToStaging(remoteFilePath,
                                                      username,
                                                      privateKeyFilePath,
                                                      host, port,
                                                      settingsModel)
            uploadModel.SetBytesUploadedToStaging(bytesUploaded)
    if 0 < bytesUploaded < fileSize:
        progressCallback(bytesUploaded, fileSize,
                         message="Found %s uploaded previously"
                         % HumanReadableSizeString(bytesUploaded))
    if foldersController.IsShuttingDown() or uploadModel.Canceled():
        logger.debug("UploadFile 1: Aborting upload for "
                     "%s" % filePath)
        return
    if bytesUploaded == fileSize:
        logger.debug("UploadFile returning because file \"%s\" has already "
                     "been uploaded." % filePath)
        return
    elif bytesUploaded > fileSize:
        logger.error("Possibly due to a bug in MyData, the file size on "
                     "the remote server is larger than the local file size "
                     "for \"%s\"." % filePath)
    elif 0 < bytesUploaded < fileSize:
        logger.info("MyData will attempt to resume the partially "
                    "completed upload for \"%s\"..." % filePath)
    elif bytesUploaded == 0:
        # The most common use case.
        progressCallback(bytesUploaded, fileSize,
                         message="Uploading...")
    if not sys.platform.startswith("win"):
        UploadFileFromPosixSystem(filePath, fileSize, username,
                                  privateKeyFilePath, host, port,
                                  remoteFilePath, progressCallback,
                                  foldersController, uploadModel,
                                  bytesUploaded)
        return
    if fileSize > largeFileSize:
        return UploadLargeFileFromWindows(filePath, fileSize, username,
                                          privateKeyFilePath, host, port,
                                          remoteFilePath, progressCallback,
                                          foldersController, uploadModel,
                                          bytesUploaded)
    else:
        return UploadSmallFileFromWindows(filePath, fileSize, username,
                                          privateKeyFilePath, host, port,
                                          remoteFilePath, progressCallback,
                                          uploadModel)


# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
def UploadFileFromPosixSystem(filePath, fileSize, username, privateKeyFilePath,
                              host, port, remoteFilePath, progressCallback,
                              foldersController, uploadModel, bytesUploaded):
    """
    On POSIX systems, we use SSH connection caching (the ControlMaster
    and ControlPath options in "man ssh_config"), but they are not
    available on Windows.

    We want to ensure that the partially uploaded datafile in MyTardis's
    staging area always has a whole number of chunks.  If we were to
    append each chunk directly to the datafile at the same time as
    sending it over the SSH channel, there would be a risk of a broken
    connection resulting in a partial chunk being appended to the datafile.
    So we upload the chunk to its own file on the remote server first,
    and then append the chunk onto the remote (partial) datafile.
    """
    remoteChunkPath = "%s/.%s.chunk" % (os.path.dirname(remoteFilePath),
                                        os.path.basename(remoteFilePath))

    settingsModel = foldersController.settingsModel
    maxThreads = settingsModel.GetMaxUploadThreads()

    if settingsModel.UseSshControlMasterIfAvailable():
        sshControlMasterPool = \
            OPENSSH.GetSshControlMasterPool(username, privateKeyFilePath,
                                            host, port)
        sshControlMasterProcess = \
            sshControlMasterPool.GetSshControlMasterProcess(maxThreads)
        sshControlPathOptionValuePair = \
            sshControlMasterProcess.GetControlPathOptionValuePair()
    else:
        sshControlPathOptionValuePair = ""

    remoteDir = os.path.dirname(remoteFilePath)
    quotedRemoteDir = OPENSSH.DoubleQuoteRemotePath(remoteDir)
    mkdirCmdAndArgs = \
        [OPENSSH.DoubleQuote(OPENSSH.ssh),
         "-p", port,
         "-i", OPENSSH.DoubleQuote(privateKeyFilePath),
         "-c", OPENSSH.cipher,
         sshControlPathOptionValuePair,
         "-oIdentitiesOnly=yes",
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
    while True:
        poll = mkdirProcess.poll()
        if poll is not None:
            break
        time.sleep(SLEEP_FACTOR * maxThreads)
    stdout, _ = mkdirProcess.communicate()
    if mkdirProcess.returncode != 0:
        logger.error("'%s' returned %d" % (mkdirCmdString,
                                           mkdirProcess.returncode))
        raise SshException(stdout, mkdirProcess.returncode)

    remoteRemoveChunkCommand = \
        "/bin/rm -f %s" % OPENSSH.DoubleQuoteRemotePath(remoteChunkPath)
    rmCommandString = \
        "%s -p %s -i %s -c %s %s " \
        "-oIdentitiesOnly=yes -oPasswordAuthentication=no " \
        "-oNoHostAuthenticationForLocalhost=yes " \
        "-oStrictHostKeyChecking=no " \
        "%s@%s %s" \
        % (OPENSSH.DoubleQuote(OPENSSH.ssh),
           port,
           privateKeyFilePath, OPENSSH.cipher,
           sshControlPathOptionValuePair,
           username, host,
           OPENSSH.DoubleQuote(remoteRemoveChunkCommand))
    logger.debug(rmCommandString)
    removeRemoteChunkProcess = \
        subprocess.Popen(rmCommandString,
                         shell=OPENSSH.preferToUseShellInSubprocess,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         startupinfo=DEFAULT_STARTUP_INFO,
                         creationflags=DEFAULT_CREATION_FLAGS)
    while True:
        poll = removeRemoteChunkProcess.poll()
        if poll is not None:
            break
        time.sleep(SLEEP_FACTOR * maxThreads)
    stdout, _ = removeRemoteChunkProcess.communicate()
    if removeRemoteChunkProcess.returncode != 0:
        raise SshException(stdout, removeRemoteChunkProcess.returncode)

    # defaultChunkSize = 1024*1024  # FIXME: magic number
    defaultChunkSize = 128 * 1024  # FIXME: magic number
    maxChunkSize = 16 * 1024 * 1024  # FIXME: magic number
    chunkSize = defaultChunkSize
    # FIXME: magic number (approximately 50 progress bar increments)
    while (fileSize / chunkSize) > 50 and chunkSize < maxChunkSize:
        chunkSize = chunkSize * 2
    skip = 0
    if 0 < bytesUploaded < fileSize and (bytesUploaded % chunkSize == 0):
        progressCallback(bytesUploaded, fileSize,
                         message="Performing seek on file, so we can "
                         "resume the upload.")
        # Using dd command on POSIX systems, so don't need fp.seek
        skip = bytesUploaded / chunkSize
        progressCallback(bytesUploaded, fileSize)
    else:
        # Overwrite staging file if it is bigger that local file:
        bytesUploaded = long(0)

    # FIXME: Handle exception where socket for ssh control path
    # is missing, then we need to create a new master connection.

    while bytesUploaded < fileSize:
        if foldersController.IsShuttingDown() or uploadModel.Canceled():
            logger.debug("UploadFileFromPosixSystem 1: Aborting upload for "
                         "%s" % filePath)
            return

        # Write chunk to temporary file:
        chunkFile = tempfile.NamedTemporaryFile(delete=False)
        chunkFile.close()
        chunkFilePath = chunkFile.name
        ddCommandString = \
            "%s bs=%d skip=%d count=1 if=%s of=%s" \
            % (OPENSSH.ddCmd,
               chunkSize,
               skip,
               OPENSSH.DoubleQuote(filePath),
               OPENSSH.DoubleQuote(chunkFilePath))
        logger.debug(ddCommandString)
        ddProcess = subprocess.Popen(
            ddCommandString,
            shell=OPENSSH.preferToUseShellInSubprocess,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        maxThreads = settingsModel.GetMaxUploadThreads()
        while True:
            poll = ddProcess.poll()
            if poll is not None:
                break
            time.sleep(SLEEP_FACTOR * maxThreads)
        stdout, _ = ddProcess.communicate()
        if ddProcess.returncode != 0:
            raise Exception(stdout,
                            ddCommandString,
                            ddProcess.returncode)
        lines = stdout.splitlines()
        bytesTransferred = long(0)
        for line in lines:
            match = re.search(r"^(\d+)\s+bytes.*$", line)
            if match:
                bytesTransferred = long(match.groups()[0])
        skip += 1

        scpCommandString = \
            '%s -v -P %s -i %s -c %s %s ' \
            '-oIdentitiesOnly=yes -oPasswordAuthentication=no ' \
            '-oNoHostAuthenticationForLocalhost=yes ' \
            '-oStrictHostKeyChecking=no ' \
            '%s "%s@%s:\\"%s\\""' \
            % (OPENSSH.DoubleQuote(OPENSSH.scp),
               port,
               privateKeyFilePath,
               OPENSSH.cipher,
               sshControlPathOptionValuePair,
               chunkFilePath,
               username, host,
               remoteChunkPath
               .replace('`', r'\\`')
               .replace('$', r'\\$'))
        logger.debug(scpCommandString)
        scpUploadChunkProcess = subprocess.Popen(
            scpCommandString,
            shell=OPENSSH.preferToUseShellInSubprocess,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        uploadModel.SetScpUploadProcess(scpUploadChunkProcess)
        while True:
            poll = scpUploadChunkProcess.poll()
            if poll is not None:
                break
            time.sleep(SLEEP_FACTOR * maxThreads)
        stdout, _ = scpUploadChunkProcess.communicate()
        if scpUploadChunkProcess.returncode != 0:
            raise ScpException(stdout,
                               scpCommandString,
                               scpUploadChunkProcess.returncode)

        # pylint: disable=bare-except
        try:
            os.unlink(chunkFile.name)
        except:
            logger.error(traceback.format_exc())

        # Append chunk to remote datafile.
        # FIXME: Investigate whether using an ampersand to put
        # remote cat process in the background helps to make things
        # more robust in the case of an interrupted connection.
        # On Windows, we might need to escape the ampersand with a
        # caret (^&)

        if bytesUploaded > 0:
            redirect = ">>"
        else:
            redirect = ">"
        remoteCatCommand = \
            "cat %s %s %s" % (OPENSSH.DoubleQuoteRemotePath(remoteChunkPath),
                              redirect,
                              OPENSSH.DoubleQuoteRemotePath(remoteFilePath))
        catCommandString = \
            "%s -p %s -i %s -c %s %s " \
            "-oIdentitiesOnly=yes -oPasswordAuthentication=no " \
            "-oNoHostAuthenticationForLocalhost=yes " \
            "-oStrictHostKeyChecking=no " \
            "%s@%s %s" \
            % (OPENSSH.DoubleQuote(OPENSSH.ssh), port,
               privateKeyFilePath,
               OPENSSH.cipher,
               sshControlPathOptionValuePair,
               username, host,
               OPENSSH.DoubleQuote(remoteCatCommand))
        # logger.debug(catCommandString)
        appendChunkProcess = subprocess.Popen(
            catCommandString,
            shell=OPENSSH.preferToUseShellInSubprocess,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        while True:
            poll = appendChunkProcess.poll()
            if poll is not None:
                break
            time.sleep(SLEEP_FACTOR * maxThreads)
        stdout, _ = appendChunkProcess.communicate()
        if appendChunkProcess.returncode != 0:
            raise SshException(stdout, appendChunkProcess.returncode)

        bytesUploaded += bytesTransferred
        progressCallback(bytesUploaded, fileSize)

        if foldersController.IsShuttingDown() or uploadModel.Canceled():
            logger.debug("UploadFileFromPosixSystem 2: Aborting upload for "
                         "%s" % filePath)
            return

    remoteRemoveChunkCommand = \
        "/bin/rm -f %s" % OPENSSH.DoubleQuoteRemotePath(remoteChunkPath)
    rmCommandString = \
        "%s -p %s -i %s -c %s %s " \
        "-oIdentitiesOnly=yes -oPasswordAuthentication=no " \
        "-oNoHostAuthenticationForLocalhost=yes " \
        "-oStrictHostKeyChecking=no " \
        "%s@%s %s" \
        % (OPENSSH.DoubleQuote(OPENSSH.ssh), port,
           privateKeyFilePath, OPENSSH.cipher,
           sshControlPathOptionValuePair,
           username, host,
           OPENSSH.DoubleQuote(remoteRemoveChunkCommand))
    # logger.debug(rmCommandString)
    removeRemoteChunkProcess = \
        subprocess.Popen(rmCommandString,
                         shell=OPENSSH.preferToUseShellInSubprocess,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         startupinfo=DEFAULT_STARTUP_INFO,
                         creationflags=DEFAULT_CREATION_FLAGS)
    while True:
        poll = removeRemoteChunkProcess.poll()
        if poll is not None:
            break
        time.sleep(SLEEP_FACTOR * maxThreads)
    stdout, _ = removeRemoteChunkProcess.communicate()
    if removeRemoteChunkProcess.returncode != 0:
        raise SshException(stdout, removeRemoteChunkProcess.returncode)

REMOTE_DIRS_CREATED = dict()

def UploadSmallFileFromWindows(filePath, fileSize, username,
                               privateKeyFilePath, host, port, remoteFilePath,
                               progressCallback, uploadModel):
    """
    Fast method for uploading small files (less overhead from chunking).
    This method don't support resuming interrupted uploads, and doesn't
    provide progress updates.
    """
    bytesUploaded = long(0)

    remoteDir = os.path.dirname(remoteFilePath)
    quotedRemoteDir = OPENSSH.DoubleQuoteRemotePath(remoteDir)
    if remoteDir not in REMOTE_DIRS_CREATED:
        mkdirCmdAndArgs = \
            [OPENSSH.DoubleQuote(OPENSSH.ssh),
             "-p", port,
             "-n",
             "-c", OPENSSH.cipher,
             "-i", OPENSSH.DoubleQuote(privateKeyFilePath),
             "-oIdentitiesOnly=yes",
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

    remoteDir = os.path.dirname(remoteFilePath)
    quotedRemoteDir = OPENSSH.DoubleQuoteRemotePath(remoteDir)
    scpCommandString = \
        '%s -v -P %s -i %s -c %s ' \
        '-oNoHostAuthenticationForLocalhost=yes ' \
        '-oPasswordAuthentication=no -oStrictHostKeyChecking=no ' \
        '%s "%s@%s:\\"%s/\\""' \
        % (OPENSSH.DoubleQuote(OPENSSH.scp), port,
           OPENSSH.DoubleQuote(GetCygwinPath(privateKeyFilePath)),
           OPENSSH.cipher,
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
    uploadModel.SetScpUploadProcess(scpUploadProcess)

    stdout, _ = scpUploadProcess.communicate()
    if scpUploadProcess.returncode != 0:
        raise ScpException(stdout, scpCommandString,
                           scpUploadProcess.returncode)
    bytesUploaded = fileSize
    progressCallback(bytesUploaded, fileSize)
    return


# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
def UploadLargeFileFromWindows(filePath, fileSize, username,
                               privateKeyFilePath, host, port,
                               remoteFilePath,
                               progressCallback, foldersController,
                               uploadModel, bytesUploaded):
    """
    We want to ensure that the partially uploaded datafile in MyTardis's
    staging area always has a whole number of chunks.  If we were to
    append each chunk directly to the datafile at the same time as
    sending it over the SSH channel, there would be a risk of a broken
    connection resulting in a partial chunk being appended to the datafile.
    So we upload the chunk to its own file on the remote server first,
    and then append the chunk onto the remote (partial) datafile.
    """

    remoteDir = os.path.dirname(remoteFilePath)
    quotedRemoteDir = OPENSSH.DoubleQuoteRemotePath(remoteDir)
    maxThreads = foldersController.settingsModel.GetMaxUploadThreads()

    mkdirCmdAndArgs = \
        [OPENSSH.DoubleQuote(OPENSSH.ssh),
         "-p", port,
         "-n",
         "-c", OPENSSH.cipher,
         "-i", OPENSSH.DoubleQuote(privateKeyFilePath),
         "-oIdentitiesOnly=yes",
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
    while True:
        poll = mkdirProcess.poll()
        if poll is not None:
            break
        time.sleep(SLEEP_FACTOR * maxThreads)
    stdout, _ = mkdirProcess.communicate()
    if mkdirProcess.returncode != 0:
        raise SshException(stdout, mkdirProcess.returncode)

    # It might seem simpler to let Python's tempfile module determine the
    # filename of the local chunk file (e.g. "tmp123"), and then assign
    # the correct name when transferring the file with scp, e.g.

    # scp tmp123 mydata@remotehost:/some/dir/.datafile001.jpg.chunk

    # However if the datafile name contains an ampersand, then escaping the
    # ampersand in the remote file path supplied to scp becomes a nightmare
    # on Windows, so it is easier to set the filename locally and only
    # specify the remote directory for scp.

    remoteChunkDir = os.path.dirname(remoteFilePath)
    chunkFilename = ".%s.chunk" % os.path.basename(remoteFilePath)
    remoteChunkPath = "%s/%s" % (remoteChunkDir, chunkFilename)
    tempChunkDir = tempfile.mkdtemp()
    chunkFilePath = os.path.join(tempChunkDir, chunkFilename)

    # logger.warning("Assuming that the remote shell is Bash.")

    defaultChunkSize = 1024 * 1024  # FIXME: magic number
    maxChunkSize = 256 * 1024 * 1024  # FIXME: magic number
    chunkSize = defaultChunkSize
    # FIXME: magic number (approximately 50 progress bar increments)
    while (fileSize / chunkSize) > 50 and chunkSize < maxChunkSize:
        chunkSize = chunkSize * 2
    skip = 0
    if 0 < bytesUploaded < fileSize and (bytesUploaded % chunkSize == 0):
        progressCallback(bytesUploaded, fileSize,
                         message="Performing seek on file, so we can "
                         "resume the upload.")
        # See "datafile.seek" below.
        skip = bytesUploaded / chunkSize
        progressCallback(bytesUploaded, fileSize)
    elif bytesUploaded > 0 and (bytesUploaded % chunkSize != 0):
        logger.debug("Setting bytesUploaded to 0, because the size of the "
                     "partially uploaded file in MyTardis's staging area "
                     "is not a whole number of chunks.")
        bytesUploaded = long(0)
    while bytesUploaded < fileSize:
        if foldersController.IsShuttingDown() or uploadModel.Canceled():
            logger.debug("UploadLargeFileFromWindows 1: "
                         "Aborting upload for %s" % filePath)
            return
        # We'll write a chunk to a temporary file.
        # chunkSize (e.g. 256 MB) is for SCP uploads
        # smallChunkSize (e.g. 8 MB) is for extracting a large chunk
        # from a datafile a little bit at a time (not wasting memory).
        with open(filePath, 'rb') as datafile:
            with open(chunkFilePath, 'wb') as chunkFile:
                logger.info("Writing chunk to %s" % chunkFilePath)
                datafile.seek(skip * chunkSize)
                bytesTransferred = long(0)
                smallChunkSize = chunkSize
                count = 1
                while (smallChunkSize > 8 * 1024 * 1024) and \
                        (smallChunkSize % 2 == 0) and count < 32:
                    smallChunkSize /= 2
                    count *= 2
                for _ in range(count):
                    smallChunk = datafile.read(smallChunkSize)
                    chunkFile.write(smallChunk)
                    bytesTransferred += len(smallChunk)
                    del smallChunk
        skip += 1

        if foldersController.IsShuttingDown() or uploadModel.Canceled():
            logger.debug("UploadLargeFileFromWindows 2: "
                         "Aborting upload for %s" % filePath)
            return

        scpCommandString = \
            '%s -v -P %s -i %s -c %s ' \
            '-oNoHostAuthenticationForLocalhost=yes ' \
            '-oPasswordAuthentication=no -oStrictHostKeyChecking=no ' \
            '%s "%s@%s:\\"%s/\\""' \
            % (OPENSSH.DoubleQuote(OPENSSH.scp), port,
               OPENSSH.DoubleQuote(GetCygwinPath(privateKeyFilePath)),
               OPENSSH.cipher,
               OPENSSH.DoubleQuote(GetCygwinPath(chunkFile.name)),
               username, host,
               remoteChunkDir
               .replace('`', r'\\`')
               .replace('$', r'\\$'))
        logger.debug(scpCommandString)
        scpUploadChunkProcess = subprocess.Popen(
            scpCommandString,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        uploadModel.SetScpUploadProcess(scpUploadChunkProcess)
        while True:
            poll = scpUploadChunkProcess.poll()
            if poll is not None:
                break
            time.sleep(SLEEP_FACTOR * maxThreads)
        stdout, _ = scpUploadChunkProcess.communicate()
        if scpUploadChunkProcess.returncode != 0:
            raise ScpException(stdout,
                               scpCommandString,
                               scpUploadChunkProcess.returncode)
        try:
            os.unlink(chunkFilePath)
        except:  # pylint: disable=bare-except
            logger.error(traceback.format_exc())
        # Append chunk to remote datafile.
        # FIXME: Investigate whether using an ampersand to put
        # remote cat process in the background helps to make things
        # more robust in the case of an interrupted connection.
        # On Windows, we might need to escape the ampersand with a
        # caret (^&)
        if bytesUploaded > 0:
            redirect = ">>"
        else:
            redirect = ">"
        remoteCatCommand = \
            "cat %s %s %s" % (OPENSSH.DoubleQuoteRemotePath(remoteChunkPath),
                              redirect,
                              OPENSSH.DoubleQuoteRemotePath(remoteFilePath))
        catCommandString = \
            "%s -p %s -n -i %s -c %s " \
            "-oNoHostAuthenticationForLocalhost=yes " \
            "-oPasswordAuthentication=no -oStrictHostKeyChecking=no " \
            "%s@%s %s" \
            % (OPENSSH.DoubleQuote(OPENSSH.ssh), port,
               OPENSSH.DoubleQuote(GetCygwinPath(privateKeyFilePath)),
               OPENSSH.cipher,
               username, host,
               OPENSSH.DoubleQuote(remoteCatCommand))
        # logger.debug(catCommandString)
        appendChunkProcess = subprocess.Popen(
            catCommandString,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        while True:
            poll = scpUploadChunkProcess.poll()
            if poll is not None:
                break
            time.sleep(SLEEP_FACTOR * maxThreads)
        stdout, _ = appendChunkProcess.communicate()
        if appendChunkProcess.returncode != 0:
            raise SshException(stdout, appendChunkProcess.returncode)

        bytesUploaded += bytesTransferred
        progressCallback(bytesUploaded, fileSize)

        if foldersController.IsShuttingDown() or uploadModel.Canceled():
            logger.debug("UploadLargeFileFromWindows 3: "
                         "Aborting upload for %s" % filePath)
            return

    try:
        os.rmdir(tempChunkDir)
    except:  # pylint: disable=bare-except
        logger.error(traceback.format_exc())


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

# Singleton instance of OpenSSH class:
OPENSSH = OpenSSH()


class SshControlMasterProcess(object):
    """
    See "ControlMaster" in "man ssh_config"
    Only available on POSIX systems.
    """
    def __init__(self, username, privateKeyFilePath, host, port):
        self.username = username
        self.privateKeyFilePath = privateKeyFilePath
        self.host = host
        self.port = port

        tempFile = tempfile.NamedTemporaryFile(delete=True)
        tempFile.close()
        if sys.platform.startswith("win"):
            self.sshControlPath = GetCygwinPath(tempFile.name)
        else:
            self.sshControlPath = tempFile.name
        sshControlMasterCommandString = \
            "%s -p %s -N -i %s -c %s " \
            "-oControlMaster=yes -oControlPath=%s " \
            "-oIdentitiesOnly=yes -oPasswordAuthentication=no " \
            "-oNoHostAuthenticationForLocalhost=yes " \
            "-oStrictHostKeyChecking=no " \
            "%s@%s" \
            % (OPENSSH.DoubleQuote(OPENSSH.ssh), port,
               privateKeyFilePath,
               OPENSSH.cipher,
               OPENSSH.DoubleQuote(self.sshControlPath),
               username, host)
        logger.debug(sshControlMasterCommandString)
        self.proc = subprocess.Popen(
            sshControlMasterCommandString,
            shell=OPENSSH.preferToUseShellInSubprocess,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        self.pid = self.proc.pid

    def Check(self, maxThreads):
        checkSshControlMasterCommand = \
            "%s -oControlPath=%s -O check " \
            "%s@%s" \
            % (OPENSSH.DoubleQuote(OPENSSH.ssh),
               OPENSSH.DoubleQuote(self.sshControlPath),
               self.username, self.host)
        logger.debug(checkSshControlMasterCommand)
        proc = subprocess.Popen(
            checkSshControlMasterCommand,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=OPENSSH.preferToUseShellInSubprocess,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        while True:
            poll = proc.poll()
            if poll is not None:
                break
            time.sleep(SLEEP_FACTOR * maxThreads)
        proc.communicate()
        return proc.returncode == 0

    def Exit(self):
        exitSshControlMasterCommand = \
            "%s -oControlPath=%s -O exit " \
            "%s@%s" \
            % (OPENSSH.DoubleQuote(OPENSSH.ssh),
               OPENSSH.DoubleQuote(self.sshControlPath),
               self.username, self.host)
        logger.debug(exitSshControlMasterCommand)
        proc = subprocess.Popen(
            exitSshControlMasterCommand,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=OPENSSH.preferToUseShellInSubprocess,
            startupinfo=DEFAULT_STARTUP_INFO,
            creationflags=DEFAULT_CREATION_FLAGS)
        proc.communicate()

    def GetControlPath(self):
        return self.sshControlPath

    def GetControlPathOptionValuePair(self):
        return "-oControlPath=%s" % OPENSSH.DoubleQuote(self.sshControlPath)

    def GetPid(self):
        return self.pid


class SshControlMasterPool(object):
    """
    Re-using an SSH connection with -oControlPath=...
    only works on POSIX systems, not on Windows.

    To avoid having too many frequent SSH connections on Windows, we can
    use larger chunk sizes (see UploadLargeFileFromWindows).
    """

    def __init__(self, username, privateKeyFilePath, host, port):
        if sys.platform.startswith("win"):
            raise NotImplementedError("-oControlMaster is not implemented "
                                      "in MinGW or Cygwin builds of OpenSSH.")
        self.username = username
        self.privateKeyFilePath = privateKeyFilePath
        self.host = host
        self.port = port
        # self.maxConnections should be less than
        # MaxSessions in staging server's sshd_config
        self.maxConnections = 5
        self.sshControlMasterProcesses = []
        self.timeout = 1

    def GetSshControlMasterProcess(self, maxThreads):
        for sshControlMasterProcess in self.sshControlMasterProcesses:
            if sshControlMasterProcess.Check(maxThreads):
                return sshControlMasterProcess
        if len(self.sshControlMasterProcesses) < self.maxConnections:
            newSshControlMasterProcess = \
                SshControlMasterProcess(self.username, self.privateKeyFilePath,
                                        self.host, self.port)
            self.sshControlMasterProcesses.append(newSshControlMasterProcess)
            return newSshControlMasterProcess
        else:
            wait = 0
            while wait < self.timeout:
                time.sleep(0.1)
                wait += 0.1
                for sshControlMasterProcess in self.sshControlMasterProcesses:
                    if sshControlMasterProcess.Check(maxThreads):
                        return sshControlMasterProcess
            message = "Exceeded max connections in SshControlMasterPool\n\n" \
                "This suggests a problem with the scp_hostname and/or " \
                "scp_username attributes of the assigned storage box."
            logger.error(message)
            logger.info("scp_hostname: %s" % self.host)
            logger.info("scp_username: %s" % self.username)
            logger.info("Private key path: %s" % self.privateKeyFilePath)
            raise SshControlMasterLimit(message)

    def ShutDown(self):
        for sshControlMasterProcess in self.sshControlMasterProcesses:
            if PidIsRunning(sshControlMasterProcess.GetPid()):
                sshControlMasterProcess.Exit()
        self.sshControlMasterProcesses = []

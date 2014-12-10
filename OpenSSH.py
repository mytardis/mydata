import sys
import os
import subprocess
import traceback
import re
import tempfile
from datetime import datetime
import errno

from logger.Logger import logger
from Exceptions import SshException
from Exceptions import ScpException
from Exceptions import StagingHostRefusedSshConnection
from Exceptions import StagingHostSshPermissionDenied
from Exceptions import PrivateKeyDoesNotExist
from UploadModel import HumanReadableSizeString


defaultStartupInfo = None
defaultCreationFlags = 0
if sys.platform.startswith("win"):
    defaultStartupInfo = subprocess.STARTUPINFO()
    defaultStartupInfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
    defaultStartupInfo.wShowWindow = subprocess.SW_HIDE
    import win32process
    defaultCreationFlags = win32process.CREATE_NO_WINDOW


class SmallFileUploadMethod():
    SCP = 0
    CAT = 1


class OpenSSH():
    OPENSSH_BUILD_DIR = 'openssh-5.4p1-1-msys-1.0.13'

    def DoubleQuote(self, x):
        return '"' + x.replace('"', '\\"') + '"'

    def SingleQuote(self, x):
        return "'" + x.replace("'", "\\'") + "'"

    def __init__(self):
        """
        Locate the SSH binaries on various systems. On Windows we bundle a
        MinGW/MSYS build of OpenSSH.
        """
        if sys.platform.startswith("win"):
            if "HOME" not in os.environ:
                os.environ["HOME"] = os.path.expanduser('~')

        if sys.platform.startswith("win"):
            if hasattr(sys, "frozen"):
                f = lambda x, y: os.path.join(os.path.dirname(sys.executable),
                                              self.OPENSSH_BUILD_DIR, x, y)
            else:
                try:
                    mydataModulePath = \
                        os.path.dirname(pkgutil.get_loader("MyData").filename)
                except:
                    mydataModulePath = os.getcwd()
                f = lambda x, y: os.path.join(mydataModulePath,
                                              self.OPENSSH_BUILD_DIR, x, y)
            self.ssh = f("bin", "ssh.exe")
            self.scp = f("bin", "scp.exe")
            self.sshKeyGen = f("bin", "ssh-keygen.exe")
            self.cipher = "arcfour"
            self.sh = f("bin", "sh.exe")
            self.pwd = f("bin", "pwd.exe")
        elif sys.platform.startswith("darwin"):
            self.ssh = "/usr/bin/ssh"
            self.scp = "/usr/bin/scp"
            self.sshKeyGen = "/usr/bin/ssh-keygen"
            self.cipher = "arcfour128"
        else:
            self.ssh = "/usr/bin/ssh"
            self.scp = "/usr/bin/scp"
            self.sshKeyGen = "/usr/bin/ssh-keygen"
            self.cipher = "arcfour128"


class KeyPair():
    def __init__(self, privateKeyFilePath, publicKeyFilePath):
        self.privateKeyFilePath = privateKeyFilePath
        self.publicKeyFilePath = publicKeyFilePath
        self.publicKey = None
        self.fingerprint = None
        self.keyType = None

    def __unicode__(self):
        return "KeyPair: " + \
            str({"privateKeyFilePath": self.privateKeyFilePath,
                 "publicKeyFilePath": self.publicKeyFilePath})

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return self.__unicode__()

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
            cmdList = [openSSH.sshKeyGen,
                       "-y",
                       "-f", openSSH.DoubleQuote(
                           GetMsysPath(self.privateKeyFilePath))]
            cmd = " ".join(cmdList)
            logger.debug(cmd)
            proc = subprocess.Popen(cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True,
                                    startupinfo=defaultStartupInfo,
                                    creationflags=defaultCreationFlags)
            stdout, _ = proc.communicate()

            if proc.returncode != 0:
                raise SshException(stdout)

            return stdout
        else:
            raise SshException("Couldn't find MyData key files in ~/.ssh "
                               "while trying to read public key.")

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
        """
        if self.publicKeyFilePath is None:
            self.publicKeyFilePath = self.privateKeyFilePath + ".pub"
        if not os.path.exists(self.publicKeyFilePath):
            publicKey = self.GetPublicKey()
            with open(self.publicKeyFilePath, "w") as pubKeyFile:
                pubKeyFile.write(publicKey)

        cmdList = [openSSH.sshKeyGen,
                   "-yl",
                   "-f",
                   openSSH.DoubleQuote(GetMsysPath(self.privateKeyFilePath))]
        cmd = " ".join(cmdList)
        logger.debug(cmd)
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                universal_newlines=True,
                                startupinfo=defaultStartupInfo,
                                creationflags=defaultCreationFlags)
        stdout, _ = proc.communicate()

        if proc.returncode != 0:
            raise SshException(stdout)

        fingerprint = None
        keyType = None
        if stdout is not None:
            sshKeyGenOutComponents = stdout.split(" ")
            if len(sshKeyGenOutComponents) > 1:
                fingerprint = sshKeyGenOutComponents[1]
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
        with open(os.path.join(keyPath, potentialKeyFile)) as f:
            for line in f:
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
        with open(os.path.join(keyPath, keyName)) as f:
            for line in f:
                if re.search(r"BEGIN .* PRIVATE KEY", line):
                    privateKeyFilePath = os.path.join(keyPath, keyName)
                    publicKeyFilePath = os.path.join(keyPath, keyName + ".pub")
                    if not os.path.exists(publicKeyFilePath):
                        publicKeyFilePath = None
                    return KeyPair(privateKeyFilePath, publicKeyFilePath)
                    break
    raise PrivateKeyDoesNotExist("Couldn't find valid private key in %s"
                                 % os.path.join(keyPath, keyName))


def NewKeyPair(keyName=None,
               keyPath=None,
               keyComment=None,
               startupinfo=defaultStartupInfo,
               creationflags=defaultCreationFlags):

    success = False

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
        cmdList = \
            [openSSH.sshKeyGen,
             "-f",
             openSSH.DoubleQuote(GetMsysPath(privateKeyFilePath)),
             "-N", '""',
             "-C", openSSH.DoubleQuote(keyComment)]
        cmd = " ".join(cmdList)
        logger.debug(cmd)
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                shell=True,
                                startupinfo=defaultStartupInfo,
                                creationflags=defaultCreationFlags)
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
    else:
        import pexpect
        args = ["-f", privateKeyFilePath,
                "-N", '""',
                "-C", openSSH.DoubleQuote(keyComment)]
        lp = pexpect.spawn(sshKeyGen, args=args)
        idx = lp.expect(["already exists",
                        pexpect.EOF])
        if idx == 0:
            raise SshException("Private key file \"%s\" already exists.")
        lp.close()
        return KeyPair(privateKeyFilePath, publicKeyFilePath)


def GetBytesUploadedToStaging(remoteFilePath, username, privateKeyFilePath,
                              hostname):
    if not remoteFilePath.startswith('"'):
        remoteFilePath = openSSH.DoubleQuote(remoteFilePath)
    cmdAndArgs = [openSSH.ssh,
                  "-i", GetMsysPath(privateKeyFilePath),
                  "-l", username,
                  "-c", openSSH.cipher,
                  "-oPasswordAuthentication=no",
                  "-oStrictHostKeyChecking=no",
                  hostname,
                  "wc -c %s" % remoteFilePath]
    logger.debug(" ".join(cmdAndArgs))
    proc = subprocess.Popen(cmdAndArgs,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            startupinfo=defaultStartupInfo,
                            creationflags=defaultCreationFlags)
    stdout, _ = proc.communicate()
    lines = stdout.splitlines()
    bytesUploaded = 0
    for line in lines:
        match = re.search(r"^(\d+)\s+\S+", line)
        if match:
            bytesUploaded = long(match.groups()[0])
            return bytesUploaded
        elif "No such file or directory" in line:
            bytesUploaded = 0
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
                "In any of these cases, it is best to contact your " \
                "MyTardis administrator for assistance." % hostname
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
                % (hostname, os.path.expanduser("~"),
                   os.path.join(os.path.expanduser("~"), ".ssh",
                                "MyData"))

            logger.error(message)
            raise StagingHostSshPermissionDenied(message)
        else:
            logger.debug(line)
    return bytesUploaded


def UploadFile(filePath, fileSize, username, privateKeyFilePath,
               hostname, remoteFilePath, ProgressCallback,
               foldersController, uploadModel):
    """
    The file may have already been uploaded, so let's check
    for it (and check its size) on the server. We don't use
    checksums here because they are slow for large files,
    and ultimately it will be the MyTardis verification
    task which does the final check.
    """

    bytesUploaded = 0
    largeFileSize = 10 * 1024 * 1024  # FIXME: Magic number

    if fileSize > largeFileSize:
        ProgressCallback(None, bytesUploaded, fileSize,
                         message="Checking for a previous partial upload...")
        bytesUploaded = GetBytesUploadedToStaging(remoteFilePath,
                                                  username, privateKeyFilePath,
                                                  hostname)
    if bytesUploaded > 0:
        ProgressCallback(None, bytesUploaded, fileSize,
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
        pass

    if fileSize > largeFileSize:
        return UploadLargeFile(filePath, fileSize, username,
                               privateKeyFilePath, hostname, remoteFilePath,
                               ProgressCallback, foldersController,
                               uploadModel, bytesUploaded)
    else:
        return UploadSmallFile(filePath, fileSize, username,
                               privateKeyFilePath, hostname, remoteFilePath,
                               ProgressCallback, foldersController,
                               uploadModel)


def UploadSmallFile(filePath, fileSize, username, privateKeyFilePath,
                    hostname, remoteFilePath, ProgressCallback,
                    foldersController, uploadModel,
                    # uploadMethod=SmallFileUploadMethod.SCP):
                    uploadMethod=SmallFileUploadMethod.CAT):
    """
    Fast methods for uploading small files (less overhead from chunking).
    These methods don't support resuming interrupted uploads.
    The CAT method provides progress updates, but the SCP method doesn't.
    See class SmallFileUploadMethod
    """
    remoteRemoveDatafileCommand = \
        "/bin/rm -f %s" % openSSH.DoubleQuote(remoteFilePath)
    rmCommandString = \
        "%s -i %s -c %s " \
        "-oPasswordAuthentication=no -oStrictHostKeyChecking=no " \
        "%s@%s %s" \
        % (openSSH.ssh, GetMsysPath(privateKeyFilePath), openSSH.cipher,
           username, hostname,
           openSSH.SingleQuote(remoteRemoveDatafileCommand))
    # logger.debug(rmCommandString)
    removeRemoteDatafileProcess = subprocess.Popen(
        rmCommandString,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        startupinfo=defaultStartupInfo,
        creationflags=defaultCreationFlags)
    stdout, _ = removeRemoteDatafileProcess.communicate()
    if removeRemoteDatafileProcess.returncode != 0:
        raise SshException(stdout, removeRemoteDatafileProcess.returncode)

    bytesUploaded = 0

    if uploadMethod == SmallFileUploadMethod.SCP:
        scpCommandString = \
            '%s -i %s -c %s ' \
            '-oPasswordAuthentication=no -oStrictHostKeyChecking=no ' \
            '%s "%s@%s:\\"%s\\""' \
            % (openSSH.scp,
               GetMsysPath(privateKeyFilePath),
               openSSH.cipher,
               openSSH.DoubleQuote(GetMsysPath(filePath)),
               username, hostname,
               os.path.dirname(remoteFilePath))
        logger.debug(scpCommandString)
        scpUploadProcess = subprocess.Popen(
            scpCommandString,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=defaultStartupInfo,
            creationflags=defaultCreationFlags, shell=True)
        uploadModel.SetScpUploadProcess(scpUploadProcess)

        stdout, _ = scpUploadProcess.communicate()
        if scpUploadProcess.returncode != 0:
            raise ScpException(stdout, scpCommandString,
                               scpUploadProcess.returncode)
        bytesUploaded = fileSize
        ProgressCallback(None, bytesUploaded, fileSize)
        return

    # uploadMethod == SmallFiledUploadMethod.CAT

    defaultChunkSize = 128*1024  # FIXME: magic number
    maxChunkSize = 1024*1024  # FIXME: magic number
    chunkSize = defaultChunkSize
    # FIXME: magic number (approximately 50 progress bar increments)
    while (fileSize / chunkSize) > 50 and chunkSize < maxChunkSize:
        chunkSize = chunkSize * 2
    remoteCatCommand = "cat >> %s" % openSSH.DoubleQuote(remoteFilePath)
    catCommandString = \
        "%s -i %s -c %s " \
        "-oPasswordAuthentication=no -oStrictHostKeyChecking=no " \
        "%s@%s %s" \
        % (openSSH.ssh, GetMsysPath(privateKeyFilePath),
           openSSH.cipher,
           username, hostname,
           openSSH.DoubleQuote(remoteCatCommand))
    # logger.debug(catCommandString)
    appendChunkProcess = subprocess.Popen(
        catCommandString,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        startupinfo=defaultStartupInfo,
        creationflags=defaultCreationFlags)
    with open(filePath, 'rb') as fp:
        for chunk in iter(lambda: fp.read(chunkSize), b''):
            if foldersController.IsShuttingDown() or uploadModel.Canceled():
                logger.debug("UploadSmallFile 1: Aborting upload for "
                             "%s" % filePath)
                return
            # Append chunk to remote datafile.
            appendChunkProcess.stdin.write(chunk)

            bytesUploaded += len(chunk)
            ProgressCallback(None, bytesUploaded, fileSize)

            if foldersController.IsShuttingDown() or uploadModel.Canceled():
                logger.debug("UploadSmallFile 2: Aborting upload for "
                             "%s" % filePath)
                try:
                    appendChunkProcess.stdin.close()
                except:
                    logger.error(traceback.format_exc())
                return
        appendChunkProcess.stdin.close()
        stdout, _ = appendChunkProcess.communicate()
        if appendChunkProcess.returncode != 0:
            raise SshException(stdout, appendChunkProcess.returncode)


def UploadLargeFile(filePath, fileSize, username, privateKeyFilePath,
                    hostname, remoteFilePath, ProgressCallback,
                    foldersController, uploadModel, bytesUploaded):
    """
    We want to ensure that the partially uploaded datafile in MyTardis's
    staging area always has a whole number of chunks.  If we were to
    append each chunk directly to the datafile at the same time as
    sending it over the SSH channel, there would be a risk of a broken
    connection resulting in a partial chunk being appended to the datafile.
    So we upload the chunk to its own file on the remote server first,
    and then append the chunk onto the remote (partial) datafile.
    """

    remoteChunkPath = remoteFilePath + ".chunk"

    # logger.warning("Assuming that the remote shell is Bash.")

    remoteRemoveChunkCommand = \
        "/bin/rm -f %s" % openSSH.DoubleQuote(remoteChunkPath)
    rmCommandString = \
        "%s -i %s -c %s " \
        "-oPasswordAuthentication=no -oStrictHostKeyChecking=no " \
        "%s@%s %s" \
        % (openSSH.ssh, GetMsysPath(privateKeyFilePath), openSSH.cipher,
           username, hostname,
           openSSH.SingleQuote(remoteRemoveChunkCommand))
    # logger.debug(rmCommandString)
    removeRemoteChunkProcess = \
        subprocess.Popen(rmCommandString,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         startupinfo=defaultStartupInfo,
                         creationflags=defaultCreationFlags)
    stdout, _ = removeRemoteChunkProcess.communicate()
    if removeRemoteChunkProcess.returncode != 0:
        raise SshException(stdout, removeRemoteChunkProcess.returncode)

    defaultChunkSize = 1024*1024  # FIXME: magic number
    maxChunkSize = 16*1024*1024  # FIXME: magic number
    chunkSize = defaultChunkSize
    # FIXME: magic number (approximately 50 progress bar increments)
    while (fileSize / chunkSize) > 50 and chunkSize < maxChunkSize:
        chunkSize = chunkSize * 2
    with open(filePath, 'rb') as fp:
        if bytesUploaded > 0 and (bytesUploaded % chunkSize == 0):
            ProgressCallback(None, bytesUploaded, fileSize,
                             message="Performing seek on file, so we can "
                             "resume the upload.")
            fp.seek(bytesUploaded)
            ProgressCallback(None, bytesUploaded, fileSize)
        for chunk in iter(lambda: fp.read(chunkSize), b''):
            if foldersController.IsShuttingDown() or uploadModel.Canceled():
                logger.debug("UploadLargeFile 1: Aborting upload for "
                             "%s" % filePath)
                return
            # Write chunk to temporary file:
            chunkFile = tempfile.NamedTemporaryFile(delete=False)
            chunkFile.write(chunk)
            chunkFile.close()
            scpCommandString = \
                '%s -i %s -c %s ' \
                '-oPasswordAuthentication=no -oStrictHostKeyChecking=no ' \
                '%s "%s@%s:\\"%s\\""' \
                % (openSSH.scp,
                   GetMsysPath(privateKeyFilePath),
                   openSSH.cipher,
                   # chunkFile.name,
                   GetMsysPath(chunkFile.name),
                   username, hostname,
                   remoteChunkPath)
            # logger.debug(scpCommandString)
            scpUploadChunkProcess = subprocess.Popen(
                scpCommandString,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                startupinfo=defaultStartupInfo,
                creationflags=defaultCreationFlags)
            uploadModel.SetScpUploadProcess(scpUploadChunkProcess)
            stdout, _ = scpUploadChunkProcess.communicate()
            if scpUploadChunkProcess.returncode != 0:
                raise ScpException(stdout,
                                   scpCommandString,
                                   scpUploadChunkProcess.returncode)
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
            remoteCatCommand = \
                "cat %s >> %s" % (openSSH.DoubleQuote(remoteChunkPath),
                                  openSSH.DoubleQuote(remoteFilePath))
            catCommandString = \
                "%s -i %s -c %s " \
                "-oPasswordAuthentication=no -oStrictHostKeyChecking=no " \
                "%s@%s %s" \
                % (openSSH.ssh, GetMsysPath(privateKeyFilePath),
                   openSSH.cipher,
                   username, hostname,
                   openSSH.DoubleQuote(remoteCatCommand))
            # logger.debug(catCommandString)
            appendChunkProcess = subprocess.Popen(
                catCommandString,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                startupinfo=defaultStartupInfo,
                creationflags=defaultCreationFlags)
            stdout, _ = appendChunkProcess.communicate()
            if appendChunkProcess.returncode != 0:
                raise SshException(stdout, appendChunkProcess.returncode)

            bytesUploaded += len(chunk)
            ProgressCallback(None, bytesUploaded, fileSize)

            if foldersController.IsShuttingDown() or uploadModel.Canceled():
                logger.debug("UploadLargeFile 2: Aborting upload for "
                             "%s" % filePath)
                return

    remoteRemoveChunkCommand = \
        "/bin/rm -f %s" % openSSH.DoubleQuote(remoteChunkPath)
    rmCommandString = \
        "%s -i %s -c %s " \
        "-oPasswordAuthentication=no -oStrictHostKeyChecking=no " \
        "%s@%s %s" \
        % (openSSH.ssh, GetMsysPath(privateKeyFilePath), openSSH.cipher,
           username, hostname,
           openSSH.SingleQuote(remoteRemoveChunkCommand))
    logger.debug(rmCommandString)
    removeRemoteChunkProcess = \
        subprocess.Popen(rmCommandString,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         startupinfo=defaultStartupInfo,
                         creationflags=defaultCreationFlags)
    stdout, _ = removeRemoteChunkProcess.communicate()
    if removeRemoteChunkProcess.returncode != 0:
        raise SshException(stdout, removeRemoteChunkProcess.returncode)


def GetMsysPath(path):
    """
    Converts "C:\path\\to\\file" to "/C/path/to/file".
    """
    realpath = os.path.realpath(path)
    match = re.search(r"^(\S):(.*)", realpath)
    if match:
        return "/" + match.groups()[0] + match.groups()[1].replace("\\", "/")
    else:
        raise Exception("OpenSSH.GetMsysPath: %s doesn't look like "
                        "a valid path." % path)

openSSH = OpenSSH()
ssh = openSSH.ssh
scp = openSSH.scp
sshKeyGen = openSSH.sshKeyGen
if sys.platform.startswith("win"):
    sh = openSSH.sh
    pwd = openSSH.pwd

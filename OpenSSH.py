import sys
import os
import subprocess
import traceback
import re
from datetime import datetime

from logger.Logger import logger
from Exceptions import SshException
from Exceptions import StagingHostRefusedSshConnection
from Exceptions import StagingHostSshPermissionDenied
from Exceptions import BrokenPipe


class OpenSSH():
    OPENSSH_BUILD_DIR = 'openssh-cygwin-stdin-build'

    def DoubleQuote(self, x):
        return '"' + x + '"'

    def __init__(self):
        """
        Locate the SSH binaries on various systems. On Windows we bundle a
        stripped-down OpenSSH build that uses Cygwin.
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
            self.sshKeyGen = f("bin", "ssh-keygen.exe")
            self.chown = f("bin", "chown.exe")
            self.chmod = f("bin", "chmod.exe")
            self.chgrp = f("bin", "chgrp.exe")
            self.cygpath = f("bin", "cygpath.exe")
            # When using bundled Cygwin binaries for SSH, we need to
            # ensure that ownership and permissions of the private
            # key file are correct (from Cygwin's perspective). Using
            # Cygwin's "ls.exe" binary with "-l" # is more accurate
            # at measuring the relevant permissions than os.stat().
            self.ls = f("bin", "ls.exe")
            self.mkgroup = f("bin", "mkgroup.exe")
            self.etcGroupPath = f("etc", "group")

            with open(self.etcGroupPath, "w") as etcGroup:
                cmdAndArgs = [self.mkgroup, "-l"]
                proc = subprocess.Popen(cmdAndArgs,
                                        stdin=subprocess.PIPE,
                                        stdout=etcGroup,
                                        stderr=subprocess.STDOUT,
                                        universal_newlines=True,
                                        shell=True,
                                        startupinfo=defaultStartupInfo,
                                        creationflags=defaultCreationFlags)
                stdout, stderr = proc.communicate()
                if proc.returncode != 0:
                    raise SshException(stderr)

            self.cipher = "arcfour"
        elif sys.platform.startswith("darwin"):
            self.ssh = "/usr/bin/ssh"
            self.sshKeyGen = "/usr/bin/ssh-keygen"
            self.chown = "/usr/sbin/chown"
            self.chmod = "/bin/chmod"
            self.chgrp = "/bin/chgrp"
            self.ls = "/bin/ls"
            self.cipher = "arcfour128"
        else:
            self.ssh = "/usr/bin/ssh"
            self.sshKeyGen = "/usr/bin/ssh-keygen"
            self.chown = "/bin/chown"
            self.chmod = "/bin/chmod"
            self.chgrp = "/bin/chgrp"
            self.ls = "/bin/ls"
            self.cipher = "arcfour128"


class KeyPair():
    def __init__(self, privateKeyFilePath, publicKeyFilePath):
        self.privateKeyFilePath = privateKeyFilePath
        self.publicKeyFilePath = publicKeyFilePath

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
        with open(self.publicKeyFilePath, "r") as pubKeyFile:
            return pubKeyFile.read()

    def Delete(self):
        try:
            os.unlink(self.privateKeyFilePath)
            if self.publicKeyFilePath is not None:
                os.unlink(self.publicKeyFilePath)
        except:
            logger.error(traceback.format_exc())
            return False

        return True

    def CheckPermissions(self):
        permissions = None
        owner = None
        group = None
        cmdAndArgs = [ls, "-l",
                      GetCygwinPath(self.privateKeyFilePath)]
        logger.debug(str(cmdAndArgs))
        proc = subprocess.Popen(cmdAndArgs,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                startupinfo=defaultStartupInfo,
                                creationflags=defaultCreationFlags)
        stdout, stderr = proc.communicate()
        logger.debug(stdout)
        for line in stdout.splitlines():
            match = re.search(r"^(\S+)\s+\d+\s+(\S+)\s+(\S+)", line)
            if match:
                permissions = match.groups()[0]
                owner = match.groups()[1]
                group = match.groups()[2]
                break
        if not match:
            raise SshException("Failed to check permissions on "
                               "private key file.")
        match1 = re.search(r"^-rw-------", permissions)
        match2 = re.search(r"^-r--------", permissions)
        if match1 or match2:
            logger.info("Permissions on private key file look OK: %s"
                        % permissions)
            return True

        if sys.platform.startswith("win"):
            if group == "None" or group == "mkpasswd":
                logger.error("Group is wrong on private key file: %s"
                             % group)
                if os.path.exists(etcGroupPath):
                    logger.debug("Group file exists: %s" % etcGroupPath)
                else:
                    logger.debug("Group file doesn't exist. "
                                 "Need to run %s" % mkgroup)
                    raise SshException("Missing group file: %s", etcGroupPath)

                cmdAndArgs = [chgrp, "Users",
                              GetCygwinPath(self.privateKeyFilePath)]
                logger.debug(str(cmdAndArgs))
                proc = subprocess.Popen(cmdAndArgs,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        shell=True,
                                        startupinfo=defaultStartupInfo,
                                        creationflags=defaultCreationFlags)
                stdout, stderr = proc.communicate()
                if proc.returncode != 0:
                    logger.error(stdout)
                    raise SshException("Failed to change private key "
                                       "file's group")
                logger.info("Set private key file's group to \"Users\".")

                cmdAndArgs = [chmod, "600",
                              GetCygwinPath(self.privateKeyFilePath)]
                logger.debug(str(cmdAndArgs))
                proc = subprocess.Popen(cmdAndArgs,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        startupinfo=defaultStartupInfo,
                                        creationflags=defaultCreationFlags)
                stdout, stderr = proc.communicate()
                if proc.returncode != 0:
                    raise SshException(stderr)
                logger.info("Set private key file's permissions to 600.")


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


def FindKeyPair(keyName, keyPath=None):
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
    return None


defaultStartupInfo = subprocess.STARTUPINFO()
defaultCreationFlags = 0
if sys.platform.startswith("win"):
    defaultStartupInfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
    defaultStartupInfo.wShowWindow = subprocess.SW_HIDE
    import win32process
    defaultCreationFlags = win32process.CREATE_NO_WINDOW


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

    if sys.platform.startswith('win'):
        cmdList = \
            [sshKeyGen, "-f",
             openSSH.DoubleQuote(privateKeyFilePath),
             "-C", openSSH.DoubleQuote(keyComment)]
        cmd = " ".join(cmdList)
        proc = subprocess.Popen(cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                shell=True,
                                startupinfo=defaultStartupInfo,
                                creationflags=defaultCreationFlags)
        stdout, stderr = proc.communicate()

        if stdout is None or str(stdout).strip() == "":
            logger.error("OpenSSH.newKeyPair: "
                         "(1) Got EOF from ssh-keygen binary")
        elif "Your identification has been saved" in stdout:
            success = True
        elif "already exists" in stdout:
            raise SshException("Private key file \"%s\" already exists."
                               % privateKeyFilePath)
        else:
            logger.error("OpenSSH.newKeyPair: "
                         "Got unknown error from ssh-keygen binary")
            logger.error("OpenSSH.newKeyPair: " + stdout)
    else:
        import pexpect

        args = ["-f", privateKeyFilePath,
                "-C", openSSH.DoubleQuote(keyComment)]
        lp = pexpect.spawn(sshKeyGen, args=args)
        idx = lp.expect(["already exists",
                        pexpect.EOF])
        if idx == 0:
            raise SshException("Private key file \"%s\" already exists.")
        else:
            raise SshException("Unexpected result from "
                               "attempt to create new key.")
        lp.close()
    publicKeyFilePath = privateKeyFilePath + ".pub"

    if success:
        return KeyPair(privateKeyFilePath, publicKeyFilePath)
    else:
        return None


def GetCygwinPath(path):
    if not path.startswith('"'):
        path = openSSH.DoubleQuote(path)
    cmdList = [cygpath] + [path]
    cmd = " ".join(cmdList)
    proc = subprocess.Popen(cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=True,
                            startupinfo=defaultStartupInfo,
                            creationflags=defaultCreationFlags)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise Exception(stderr)
    cygwinPath = stdout.strip()
    return cygwinPath


def GetBytesUploadedToStaging(remoteFilePath, username, privateKeyFilePath,
                              hostname):
    if not remoteFilePath.startswith('"'):
        remoteFilePath = openSSH.DoubleQuote(remoteFilePath)
    cmdAndArgs = [ssh,
                  "-i", privateKeyFilePath,
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
    stdout, stderr = proc.communicate()
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
        elif "Broken pipe" in line:
            message = "An error occurred while trying to upload data to " \
                "MyTardis's staging host.\n\n"
            message += line
            logger.error(message)
            raise BrokenPipe(message)
        else:
            logger.debug(line)
    return bytesUploaded

def UploadFile(filePath, fileSize, username, privateKeyFilePath,
               hostname, remoteFilePath, progressCallback,
               foldersController, uploadModel):
    if not remoteFilePath.startswith('"'):
        remoteFilePath = openSSH.DoubleQuote(remoteFilePath)
    # The file may have already been uploaded, so let's check
    # for it (and check its size) on the server. We don't use
    # checksums here because they are slow for large files,
    # and ultimately it will be the MyTardis verification
    # task which does the final check.
    bytesUploaded = GetBytesUploadedToStaging(remoteFilePath,
                                              username, privateKeyFilePath,
                                              hostname)
    if bytesUploaded == fileSize:
        logger.debug("UploadFile returning because file \"%s\" has already "
                     "been uploaded." % filePath)
        return
    elif bytesUploaded > fileSize:
        logger.error("Possibly due to a bug in MyData, the file size on "
                     "the remote server is larger than the local file size "
                     "for \"%s\"." % filePath)
    elif 0 < bytesUploaded < fileSize:
        logger.warning("FIXME: MyData should be able to resume partially "
                       "completed uploads, but for now, we'll restart the "
                       "upload for \"%s\"..." % filePath)
    elif bytesUploaded == 0:
        # The most common use case.
        pass

    remoteCommandWithRm = "/bin/rm -f %s && cat >> %s" \
        % (remoteFilePath, remoteFilePath)
    remoteCommandWithoutRm = "cat >> %s" % remoteFilePath
    cmdAndArgs = [ssh,
                  "-i", privateKeyFilePath,
                  "-l", username,
                  "-c", openSSH.cipher,
                  "-oPasswordAuthentication=no",
                  "-oStrictHostKeyChecking=no",
                  "-oServerAliveInterval=30",
                  hostname,
                  remoteCommandWithRm]
    logger.debug(" ".join(cmdAndArgs))
    sshConnectionStartTime = datetime.now()
    proc = subprocess.Popen(cmdAndArgs,
                            stdin=subprocess.PIPE,
                            startupinfo=defaultStartupInfo,
                            creationflags=defaultCreationFlags)
    chunkSize = 102400
    oneMegabyte = 1048576
    while (fileSize / chunkSize) > 100 and chunkSize < oneMegabyte:
        chunkSize = chunkSize * 2
    with open(filePath, 'rb') as fp:
        bytesWritten = 0
        for chunk in iter(lambda: fp.read(chunkSize), b''):
            if foldersController.IsShuttingDown() or uploadModel.Canceled():
                logger.debug("Aborting upload for "
                             "%s" % filePath)
                proc.terminate()
                return None
            currentTime = datetime.now()
            elapsedTime = currentTime - sshConnectionStartTime
            # FIXME: SSH connection refresh time should be configurable:
            if elapsedTime.total_seconds() >= 300:
                # If SSH processes are left open for too long,
                # we can get "Write Failed: Broken pipe" errors.
                proc.terminate()
                cmdAndArgs = [ssh,
                              "-i", privateKeyFilePath,
                              "-l", username,
                              "-c", openSSH.cipher,
                              "-oPasswordAuthentication=no",
                              "-oStrictHostKeyChecking=no",
                              "-oServerAliveInterval=30",
                              hostname,
                              remoteCommandWithoutRm]
                logger.debug(" ".join(cmdAndArgs))
                sshConnectionStartTime = datetime.now()
                proc = subprocess.Popen(
                    cmdAndArgs,
                    stdin=subprocess.PIPE,
                    startupinfo=defaultStartupInfo,
                    creationflags=defaultCreationFlags)
            try:
                proc.stdin.write(chunk)
            except IOError, e:
                print "FIXME: Should be able to roll back to beginning " \
                    "of the current chunk and resume upload when we get a " \
                    "\"Write Failed: Broken pipe\" error."
                message = "An error occurred while trying to upload data to " \
                    "MyTardis's staging host.\n\n"
                message += str(e)
                logger.error(message)
                if "Broken pipe" in message:
                    raise BrokenPipe(message)
                else:
                    raise
            bytesWritten += len(chunk)
            progressCallback(None, bytesWritten, fileSize)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        logger.error(" ".join(cmdAndArgs))
        logger.error(stdout)
        raise SshException(stdout)

openSSH = OpenSSH()
ssh = openSSH.ssh
sshKeyGen = openSSH.sshKeyGen
chown = openSSH.chown
chmod = openSSH.chmod
chgrp = openSSH.chgrp
ls = openSSH.ls
if sys.platform.startswith("win"):
    cygpath = openSSH.cygpath
    etcGroupPath = openSSH.etcGroupPath
    mkgroup = openSSH.mkgroup

import sys
import os
import subprocess
import traceback
from os.path import expanduser
import re

from logger.Logger import logger


class OpenSSH():

    OPENSSH_BUILD_DIR = 'openssh-cygwin-stdin-build'

    def doubleQuote(self, x):
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
                f = lambda x: os.path.join(os.path.dirname(sys.executable),
                                           self.OPENSSH_BUILD_DIR, "bin", x)
            else:
                try:
                    mydataModulePath = \
                        os.path.dirname(pkgutil.get_loader("MyData").filename)
                except:
                    mydataModulePath = os.getcwd()
                f = lambda x: os.path.join(mydataModulePath,
                                           self.OPENSSH_BUILD_DIR, "bin", x)
            self.ssh = self.doubleQuote(f("ssh.exe"))
            self.sshKeyGen = self.doubleQuote(f("ssh-keygen.exe"))
            self.chown = self.doubleQuote(f("chown.exe"))
            self.chmod = self.doubleQuote(f("chmod.exe"))
        elif sys.platform.startswith("darwin"):
            self.ssh = "/usr/bin/ssh"
            self.sshKeyGen = "/usr/bin/ssh-keygen"
            self.chown = "/usr/sbin/chown"
            self.chmod = "/bin/chmod"
        else:
            self.ssh = "/usr/bin/ssh"
            self.sshKeyGen = "/usr/bin/ssh-keygen"
            self.chown = "/bin/chown"
            self.chmod = "/bin/chmod"


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

    def publicKey(self):
        with open(self.publicKeyFilePath, "r") as pubKeyFile:
            return pubKeyFile.read()

    def delete(self):
        try:
            os.unlink(self.privateKeyFilePath)
            if self.publicKeyFilePath is not None:
                os.unlink(self.publicKeyFilePath)
        except:
            logger.error(traceback.format_exc())
            return False

        return True


def listKeyPairs(keyPath=None):
    if keyPath is None:
        keyPath = os.path.join(expanduser('~'), ".ssh")
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


def findKeyPair(keyName, keyPath=None):
    if keyPath is None:
        keyPath = os.path.join(expanduser('~'), ".ssh")
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


def newKeyPair(keyName=None,
               keyPath=None,
               keyComment=None,
               startupinfo=defaultStartupInfo,
               creationflags=defaultCreationFlags):

    success = False

    if keyName is None:
        keyName = "MyData"
    if keyPath is None:
        keyPath = os.path.join(expanduser('~'), ".ssh")
    if keyComment is None:
        keyComment = "MyData Key"
    privateKeyFilePath = os.path.join(keyPath, keyName)

    if sys.platform.startswith('win'):
        cmdList = \
            [sshKeyGen, "-f",
             openSSH.doubleQuote(privateKeyFilePath),
             "-C", openSSH.doubleQuote(keyComment)]
        cmd = " ".join(cmdList)
        proc = subprocess.Popen(cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                universal_newlines=True,
                                shell=True,
                                startupinfo=startupinfo,
                                creationflags=creationflags)
        stdout, stderr = proc.communicate()

        if stdout is None or str(stdout).strip() == "":
            logger.error("KeyModel.generateNewKey: "
                         "(1) Got EOF from ssh-keygen binary")
        elif "Your identification has been saved" in stdout:
            success = True
        elif "already exists" in stdout:
            raise Exception("Private key file \"%s\" already exists."
                            % privateKeyFilePath)
        else:
            logger.error("KeyModel.generateNewKey: "
                         "Got unknown error from ssh-keygen binary")
            logger.error("KeyModel.generateNewKey: " + stdout)
    else:
        import pexpect

        args = ["-f", privateKeyFilePath,
                "-C", openSSH.doubleQuote(keyComment)]
        lp = pexpect.spawn(sshKeyGen, args=args)
        idx = lp.expect(["already exists",
                        pexpect.EOF])
        if idx == 0:
            raise Exception("Private key file \"%s\" already exists.")
        else:
            raise Exception("Unexpected result from "
                            "attempt to create new key.")
        lp.close()
    publicKeyFilePath = privateKeyFilePath + ".pub"

    if success:
        return KeyPair(privateKeyFilePath, publicKeyFilePath)
    else:
        return None


openSSH = OpenSSH()

ssh = openSSH.ssh
sshKeyGen = openSSH.sshKeyGen
chown = openSSH.chown
chmod = openSSH.chmod

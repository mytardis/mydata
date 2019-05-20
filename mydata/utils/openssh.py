"""
Methods for using OpenSSH functionality from MyData.

Previous MyData versions used SSH/SCP with a Cygwin build of OpenSSH on Windows

MyData is now using Paramiko SFTP
"""
import base64
import hashlib
from datetime import datetime
import getpass
import os
import re
import sys
import threading
import traceback

import paramiko

from ..events.stop import ShouldCancelUpload
from ..settings import SETTINGS
from ..logs import logger
from ..utils.exceptions import PrivateKeyDoesNotExist
from ..threads.locks import LOCKS

from .progress import MonitorProgress

REMOTE_DIRS_CREATED = dict()


class KeyPair(object):
    """
    Represents an SSH key-pair, e.g. (~/.ssh/MyData, ~/.ssh/MyData.pub)
    """
    def __init__(self, privateKey, privateKeyFilePath, publicKeyFilePath):

        #: The private key, an object of class `paramiko.rsakey.RSAKey`
        self.privateKey = privateKey

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
        return None

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
        Return the MD5 hash of the Base64-decoded public key and the
        key type (e.g. 'ssh-rsa')
        """
        if not os.path.exists(self.privateKeyFilePath):
            raise PrivateKeyDoesNotExist("Couldn't find valid private key in "
                                         "%s" % self.privateKeyFilePath)
        if self.publicKeyFilePath is None:
            self.publicKeyFilePath = self.privateKeyFilePath + ".pub"
        if not os.path.exists(self.publicKeyFilePath):
            with open(self.publicKeyFilePath, "w") as pubKeyFile:
                pubKeyFile.write(self.publicKey)

        self.privateKey = paramiko.RSAKey.from_private_key_file(
            self.privateKeyFilePath)

        digest = hashlib.md5(base64.b64decode(
            self.privateKey.get_base64().encode('ascii'))).hexdigest()
        fingerprint = ':'.join(re.findall('..', digest))

        keyType = self.privateKey.get_name()

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
    if not keyPath:
        keyPath = GetKeyPairLocation()
    if os.path.exists(os.path.join(keyPath, keyName)):
        with open(os.path.join(keyPath, keyName)) as keyFile:
            for line in keyFile:
                if re.search(r"BEGIN .* PRIVATE KEY", line):
                    privateKeyFilePath = os.path.join(keyPath, keyName)
                    privateKey = paramiko.RSAKey.from_private_key_file(
                        privateKeyFilePath)
                    publicKeyFilePath = os.path.join(keyPath, keyName + ".pub")
                    if not os.path.exists(publicKeyFilePath):
                        publicKeyFilePath = None
                    return KeyPair(privateKey, privateKeyFilePath,
                                   publicKeyFilePath)
    return None


def NewKeyPair(keyName=None, keyPath=None, keyComment=None):
    """
    Create an RSA key-pair in ~/.ssh/ (or in keyPath if specified)
    for use with SFTP
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

    privateKey = paramiko.RSAKey.generate(bits=2048)
    privateKey.write_private_key_file(filename=privateKeyFilePath)
    publicKey = paramiko.RSAKey(filename=privateKeyFilePath)
    with open(publicKeyFilePath, "w") as publicKeyFile:
        publicKeyFile.write("%s %s" % (publicKey.get_name(),
                                       publicKey.get_base64()))
        publicKeyFile.write(" %s" % keyComment)
    return KeyPair(privateKey, privateKeyFilePath, publicKeyFilePath)


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


def UploadFile(filePath, fileSize, username, privateKey,
               host, port, remoteFilePath, progressCallback,
               uploadModel):
    """
    Upload a file to staging using SFTP.

    Ignore bytes uploaded previously, because MyData is no longer
    chunking files, so with SFTP, we will always upload the whole
    file.
    """
    progressCallback(current=0, total=fileSize, message="Uploading...")

    monitoringProgress = threading.Event()
    uploadModel.startTime = datetime.now()
    MonitorProgress(SETTINGS.miscellaneous.progressPollInterval, uploadModel,
                    fileSize, monitoringProgress, progressCallback)

    uploadThread = threading.current_thread()
    if not hasattr(uploadThread, "paramikoTransport"):
        uploadThread.paramikoTransport = paramiko.Transport((host, int(port)))
        uploadThread.paramikoTransport.connect(
            username=username, pkey=privateKey)
        uploadThread.paramikoSftp = paramiko.SFTPClient.from_transport(
            uploadThread.paramikoTransport)
        uploadThread.paramikoSftp.get_channel().settimeout(
            SETTINGS.miscellaneous.connectionTimeout)
        assert uploadThread.paramikoSftp

    remoteDir = os.path.dirname(remoteFilePath)
    with LOCKS.createRemoteDir:
        MakeRemoteDirs(uploadThread.paramikoSftp, remoteDir)

    if ShouldCancelUpload(uploadModel):
        logger.debug("UploadFile: Aborting upload for %s" % filePath)
        return

    logger.debug("sftp.put(%s, %s)" % (filePath, remoteFilePath))
    uploadThread.paramikoSftp.put(filePath, remoteFilePath)

    uploadThread.paramikoSftp.chmod(remoteFilePath, 0o660)

    uploadModel.SetLatestTime(datetime.now())
    progressCallback(current=fileSize, total=fileSize)


def MakeRemoteDirs(paramikoSftp, remoteDir):
    """Change to this directory, recursively making new folders if needed.
    Returns True if any folders were created."""
    if os.path.dirname(remoteDir) == remoteDir:
        # e.g. '/' or ''C:\'
        return False
    if remoteDir == '':
        # top-level relative directory must exist
        return False
    try:
        paramikoSftp.stat(remoteDir)
        # If subdirectory exists, no IOError is thrown:
        return False
    except IOError:
        dirname = os.path.dirname(remoteDir.rstrip('/').rstrip('\\'))
        # Make parent directories:
        MakeRemoteDirs(paramikoSftp, dirname)
        # Subdirectory missing, so create it:
        paramikoSftp.mkdir(remoteDir, 0o770)
        REMOTE_DIRS_CREATED[remoteDir] = True
        return True

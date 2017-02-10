"""
mydata/models/uploader.py

The purpose of this module is to help with registering MyData uploaders
(which are usually instrument PCs) with the MyTardis server.

MyData POSTs some basic information about the PC and about the MyData
installation to its MyTardis server.  This basic information is called an
"Uploader" record.  The Uploader is made unique by a locally-generated
UUID, so each MyData instance should only have one Uploader record in MyTardis.

Initially only HTTP POST uploads are enabled in MyData, but MyData will
request uploads via SCP to a staging area, and wait for a MyTardis
administrator to approve the request (which requires updating the
UploaderRegistrationRequest record created by MyData in the Djano Admin
interface).

The IP address information provided in the Uploader record can be used
on the SCP server to grant access via /etc/hosts.allow or equivalent.

When the MyTardis administrator approves the UploaderRegistrationRequest,
they will link the request to a MyTardis StorageBox, which must have
StorageBoxAttributes for the following keys: "scp_username", "scp_hostname".

The first time a particular scp_username and scp_hostname are used, the
MyTardis administrator needs to ensure that the "scp_username" account
has been set up properly on the staging host.  (The staging host can
be the same as the MyTardis server, or it can be another host which
mounts the same storage.)

Below is a sample of a MyTardis administrator's notes made when adding a
new scp_username ("mydata") and scp_hostname ("118.138.241.33")
to a storage box for the first time, and at the same time, adding the SSH
public key sent in the UploaderRegistrationRequest into that user's
authorized_keys file.

Ran the following as root on the staging host (118.138.241.33) :

$ adduser mydata
$ mkdir /home/mydata/.ssh
$ echo "ssh-rsa AAAAB3NzaC... MyData Key" > /home/mydata/.ssh/authorized_keys
$ chown -R mydata:mydata /home/mydata/.ssh/
$ chmod 700 /home/mydata/.ssh/
$ chmod 600 /home/mydata/.ssh/authorized_keys
$ usermod -a -G mytardis mydata

N.B.: The test below was only possible because the MyData user submitting the
request and the MyTardis administrator approving the request were the same
person.  Normally, the MyTardis administrator wouldn't have access to the
MyData user's private key.

$ ssh -i ~/.ssh/MyData mydata@118.138.241.33
[mydata@118.138.241.33 ~]$ groups
mydata mytardis
[mydata@118.138.241.33 ~]$ ls -lh /var/lib/mytardis | grep receiving
drwxrws--- 8 mytardis mytardis 4096 May 15 13:30 receiving
[mydata@118.138.241.33 ~]$ touch /var/lib/mytardis/receiving/test123.txt
[mydata@118.138.241.33 ~]$ ls -l /var/lib/mytardis/receiving/test123.txt
-rw-rw-r-- 1 mydata mytardis 0 May 15 13:40 /var/lib/mytardis/receiving/test123.txt

Note the permissions above - being part of the "mytardis" group on this staging
host allows the "mydata" user to write to the staging (receiving) directory,
but not to MyTardis's permanent storage location.

The 's' in the "receiving" directory's permissions (set with 'chmod g+s') is
important.  It means that files created within that directory by the "mydata"
user will have a default group of "mytardis" (inherited from the "receiving"
directory), instead of having a default group of "mydata".
"""

import json
import os
import sys
import platform
import getpass
import re
import pkgutil
import urllib
import traceback
import uuid
import threading

import dateutil.parser
import netifaces
import psutil
import requests

from mydata import __version__ as VERSION
from mydata.models.storage import StorageBox
from mydata.logs import logger
import mydata.utils.openssh as OpenSSH
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import PrivateKeyDoesNotExist
from mydata.utils.exceptions import MissingMyDataAppOnMyTardisServer
from mydata.utils.exceptions import StorageBoxOptionNotFound
from mydata.utils.exceptions import StorageBoxAttributeNotFound
from mydata.utils import BytesToHuman
from . import HandleHttpError

DEFAULT_TIMEOUT = 3


class UploaderModel(object):
    """
    Model class for MyTardis API v1's UploaderAppResource.
    See: https://github.com/mytardis/mytardis-app-mydata/blob/master/api.py
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, settingsModel):
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        self.settingsModel = settingsModel
        self.interface = None
        self.responseJson = None

        self.uploaderId = None
        self.uploaderSettings = None
        self.settingsUpdated = None
        self.uuid = self.settingsModel.GetUuid()
        if self.uuid is None:
            self.GenerateUuid()
            self.settingsModel.SetUuid(self.uuid)

        self.osUsername = ""
        self.cpus = 0
        self.osPlatform = ""
        self.hostname = ""
        self.machine = ""
        self.osVersion = ""
        self.requestStagingAccessThreadLock = threading.Lock()
        self.memory = ""
        self.osSystem = ""
        self.architecture = ""
        self.osRelease = ""
        self.processor = ""
        self.architecture = ""

        if netifaces.AF_INET in netifaces.gateways()['default'].keys():
            self.interface = \
                netifaces.gateways()['default'][netifaces.AF_INET][1]
            ifaddresses = netifaces.ifaddresses(self.interface)
            self.macAddress = ifaddresses[netifaces.AF_LINK][0]['addr']
            ipv4Addrs = ifaddresses[netifaces.AF_INET]
            self.ipv4Address = ipv4Addrs[0]['addr']
            self.subnetMask = ipv4Addrs[0]['netmask']
            ipv6Addrs = \
                netifaces.ifaddresses(self.interface)[netifaces.AF_INET6]
            if sys.platform.startswith("win"):
                self.ipv6Address = ipv6Addrs[0]['addr']
            else:
                for addr in ipv6Addrs:
                    match = re.match(r'(.+)%(.+)', addr['addr'])
                    if match and match.group(2) == self.interface:
                        self.ipv6Address = match.group(1)
            logger.debug("The active network interface is: %s"
                         % str(self.interface))
        else:
            logger.warning("There is no active network interface.")

        self.name = self.settingsModel.GetInstrumentName()
        self.contactName = self.settingsModel.GetContactName()
        self.contactEmail = self.settingsModel.GetContactEmail()

        self.userAgentName = "MyData"
        self.userAgentVersion = VERSION
        self.userAgentInstallLocation = ""

        if hasattr(sys, 'frozen'):
            self.userAgentInstallLocation = os.path.dirname(sys.executable)
        else:
            try:
                self.userAgentInstallLocation = \
                    os.path.dirname(pkgutil.get_loader("MyData").filename)
            except:
                self.userAgentInstallLocation = os.getcwd()

        fmt = "%-17s %8s %8s %8s %5s%% %9s  %s\n"
        diskUsage = fmt % ("Device", "Total", "Used", "Free", "Use ", "Type",
                           "Mount")

        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt':
                if 'cdrom' in part.opts or part.fstype == '':
                    # skip cd-rom drives with no disk in it; they may raise
                    # ENOENT, pop-up a Windows GUI error for a non-ready
                    # partition or just hang.
                    continue
            usage = psutil.disk_usage(part.mountpoint)
            diskUsage += fmt % (
                part.device,
                BytesToHuman(usage.total),
                BytesToHuman(usage.used),
                BytesToHuman(usage.free),
                int(usage.percent),
                part.fstype,
                part.mountpoint)

        self.diskUsage = diskUsage.strip()
        self.dataPath = self.settingsModel.GetDataDirectory()
        self.defaultUser = self.settingsModel.GetUsername()

    def UploadUploaderInfo(self):
        """ Uploads info about the instrument PC to MyTardis via HTTP POST """
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        url = myTardisUrl + "/api/v1/mydata_uploader/?format=json" + \
            "&uuid=" + urllib.quote(self.uuid)
        try:
            headers = self.settingsModel.GetDefaultHeaders()
            response = requests.get(headers=headers, url=url,
                                    timeout=DEFAULT_TIMEOUT)
        except Exception, err:
            logger.error(str(err))
            raise
        if response.status_code == 404:
            message = "The MyData app is missing from the MyTardis server."
            logger.error(url)
            logger.error(message)
            raise MissingMyDataAppOnMyTardisServer(message)
        if response.status_code == 200:
            existingUploaderRecords = response.json()
        else:
            HandleHttpError(response)
        numExistingUploaderRecords = \
            existingUploaderRecords['meta']['total_count']
        if numExistingUploaderRecords > 0:
            self.uploaderId = existingUploaderRecords['objects'][0]['id']
            if 'settings' in existingUploaderRecords['objects'][0]:
                self.uploaderSettings = \
                    existingUploaderRecords['objects'][0]['settings']
                settingsUpdatedString = \
                    existingUploaderRecords['objects'][0]['settings_updated']
                logger.info(settingsUpdatedString)
                if settingsUpdatedString:
                    self.settingsUpdated = \
                        dateutil.parser.parse(settingsUpdatedString)

        logger.debug("Uploading uploader info to MyTardis...")

        if numExistingUploaderRecords > 0:
            url = myTardisUrl + "/api/v1/mydata_uploader/%d/" % self.uploaderId
        else:
            url = myTardisUrl + "/api/v1/mydata_uploader/"

        self.osPlatform = sys.platform
        self.osSystem = platform.system()
        self.osRelease = platform.release()
        self.osVersion = platform.version()
        self.osUsername = getpass.getuser()

        self.machine = platform.machine()
        self.architecture = str(platform.architecture())
        self.processor = platform.processor()
        self.memory = BytesToHuman(psutil.virtual_memory().total)
        self.cpus = psutil.cpu_count()

        self.hostname = platform.node()

        uploaderJson = {"uuid": self.uuid,
                        "name": self.name,
                        "contact_name": self.contactName,
                        "contact_email": self.contactEmail,

                        "user_agent_name": self.userAgentName,
                        "user_agent_version": self.userAgentVersion,
                        "user_agent_install_location":
                            self.userAgentInstallLocation,

                        "os_platform": self.osPlatform,
                        "os_system": self.osSystem,
                        "os_release": self.osRelease,
                        "os_version": self.osVersion,
                        "os_username": self.osUsername,

                        "machine": self.machine,
                        "architecture": self.architecture,
                        "processor": self.processor,
                        "memory": self.memory,
                        "cpus": self.cpus,

                        "disk_usage": self.diskUsage,
                        "data_path": self.dataPath,
                        "default_user": self.defaultUser,

                        "interface": self.interface,
                        "mac_address": self.macAddress,
                        "ipv4_address": self.ipv4Address,
                        "ipv6_address": self.ipv6Address,
                        "subnet_mask": self.subnetMask,

                        "hostname": self.hostname,

                        "instruments": [self.settingsModel.GetInstrument()
                                        .GetResourceUri()]}

        data = json.dumps(uploaderJson, indent=4)
        logger.debug(data)
        headers = self.settingsModel.GetDefaultHeaders()
        if numExistingUploaderRecords > 0:
            response = requests.put(headers=headers, url=url, data=data,
                                    timeout=DEFAULT_TIMEOUT)
        else:
            response = requests.post(headers=headers, url=url, data=data,
                                     timeout=DEFAULT_TIMEOUT)
        if response.status_code in (200, 201):
            logger.debug("Upload succeeded for uploader info.")
            self.responseJson = response.json()
        else:
            HandleHttpError(response)

    def ExistingUploadToStagingRequest(self):
        """
        Look for existing upload to staging request.
        """
        try:
            keyPair = self.settingsModel.GetSshKeyPair()
            if not keyPair:
                keyPair = OpenSSH.FindKeyPair("MyData")
        except PrivateKeyDoesNotExist:
            keyPair = OpenSSH.NewKeyPair("MyData")
        self.settingsModel.SetSshKeyPair(keyPair)
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        url = myTardisUrl + \
            "/api/v1/mydata_uploaderregistrationrequest/?format=json" + \
            "&uploader__uuid=" + self.uuid + \
            "&requester_key_fingerprint=" + \
            urllib.quote(keyPair.GetFingerprint())
        logger.debug(url)
        headers = self.settingsModel.GetDefaultHeaders()
        response = requests.get(headers=headers, url=url)
        if response.status_code != 200:
            HandleHttpError(response)
        logger.debug(response.text)
        existingUploaderRecords = response.json()
        numExistingUploaderRecords = \
            existingUploaderRecords['meta']['total_count']
        if numExistingUploaderRecords > 0:
            approvalJson = existingUploaderRecords['objects'][0]
            logger.debug("A request already exists for this uploader.")
            return UploaderRegistrationRequest(
                settingsModel=self.settingsModel,
                uploaderRegRequestJson=approvalJson)
        else:
            message = "This uploader hasn't requested uploading " \
                      "via staging yet."
            logger.debug(message)
            raise DoesNotExist(message)

    def RequestUploadToStagingApproval(self):
        """
        Used to request the ability to upload via SCP
        to a staging area, and then register in MyTardis.
        """
        try:
            keyPair = self.settingsModel.GetSshKeyPair()
            if not keyPair:
                keyPair = OpenSSH.FindKeyPair("MyData")
        except PrivateKeyDoesNotExist:
            keyPair = OpenSSH.NewKeyPair("MyData")
        self.settingsModel.SetSshKeyPair(keyPair)
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        url = myTardisUrl + "/api/v1/mydata_uploaderregistrationrequest/"
        uploaderRegistrationRequestJson = \
            {"uploader": self.responseJson['resource_uri'],
             "name": self.name,
             "requester_name": self.contactName,
             "requester_email": self.contactEmail,
             "requester_public_key": keyPair.GetPublicKey(),
             "requester_key_fingerprint": keyPair.GetFingerprint()}
        data = json.dumps(uploaderRegistrationRequestJson)
        headers = self.settingsModel.GetDefaultHeaders()
        response = requests.post(headers=headers, url=url, data=data)
        if response.status_code == 201:
            responseJson = response.json()
            return UploaderRegistrationRequest(
                settingsModel=self.settingsModel,
                uploaderRegRequestJson=responseJson)
        else:
            HandleHttpError(response)

    def RequestStagingAccess(self):
        """
        This could be called from multiple threads simultaneously,
        so it requires locking.
        """
        if self.requestStagingAccessThreadLock.acquire(False):
            try:
                try:
                    self.UploadUploaderInfo()
                except:
                    logger.error(traceback.format_exc())
                    raise
                try:
                    uploadToStagingRequest = \
                        self.ExistingUploadToStagingRequest()
                except DoesNotExist:
                    uploadToStagingRequest = \
                        self.RequestUploadToStagingApproval()
                    logger.debug("Uploader registration request created.")
                except PrivateKeyDoesNotExist:
                    logger.debug(
                        "Generating new uploader registration request, "
                        "because private key was moved or deleted.")
                    uploadToStagingRequest = \
                        self.RequestUploadToStagingApproval()
                    logger.debug("Generated new uploader registration request,"
                                 " because private key was moved or deleted.")
                if uploadToStagingRequest.IsApproved():
                    logger.debug("Uploads to staging have been approved!")
                else:
                    logger.debug(
                        "Uploads to staging haven't been approved yet.")
                self.settingsModel\
                    .SetUploadToStagingRequest(uploadToStagingRequest)
            except:
                logger.error(traceback.format_exc())
                raise
            finally:
                self.requestStagingAccessThreadLock.release()

    def UpdateSettings(self, settingsList):
        """
        Used to save uploader settings to the mytardis-app-mydata's
        UploaderSettings model on the MyTardis server.
        """
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        headers = self.settingsModel.GetDefaultHeaders()

        if not self.uploaderId:
            url = myTardisUrl + "/api/v1/mydata_uploader/?format=json" + \
                                "&uuid=" + urllib.quote(self.uuid)
            try:
                response = requests.get(headers=headers, url=url)
            except Exception, err:
                logger.error(str(err))
                raise
            if response.status_code == 404:
                message = "The MyData app is missing from the MyTardis server."
                logger.error(url)
                logger.error(message)
                raise MissingMyDataAppOnMyTardisServer(message)
            if response.status_code == 200:
                existingUploaderRecords = response.json()
            else:
                HandleHttpError(response)
            numExistingUploaderRecords = \
                existingUploaderRecords['meta']['total_count']
            if numExistingUploaderRecords > 0:
                self.uploaderId = existingUploaderRecords['objects'][0]['id']
            else:
                logger.debug("Uploader record doesn't exist yet, so "
                             "we can't save settings to the server.")
                return

        url = "%s/api/v1/mydata_uploader/%s/" % (myTardisUrl, self.uploaderId)

        patchData = {
            'settings': settingsList,
            'uuid': self.uuid
        }
        response = requests.patch(headers=headers, url=url,
                                  data=json.dumps(patchData))
        if response.status_code != 202:
            HandleHttpError(response)

    def GetSettings(self):
        """
        Used to retrieve uploader settings from the mytardis-app-mydata's
        UploaderSettings model on the MyTardis server.
        """
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        headers = self.settingsModel.GetDefaultHeaders()
        url = myTardisUrl + "/api/v1/mydata_uploader/?format=json" + \
                            "&uuid=" + urllib.quote(self.uuid)
        try:
            response = requests.get(headers=headers, url=url,
                                    timeout=DEFAULT_TIMEOUT)
        except Exception, err:
            logger.error(str(err))
            raise
        if response.status_code == 404:
            message = "The MyData app is missing from the MyTardis server."
            logger.error(url)
            logger.error(message)
            raise MissingMyDataAppOnMyTardisServer(message)
        if response.status_code == 200:
            existingUploaderRecords = response.json()
        else:
            HandleHttpError(response)
        numExistingUploaderRecords = \
            existingUploaderRecords['meta']['total_count']
        if numExistingUploaderRecords > 0:
            if 'id' in existingUploaderRecords['objects'][0]:
                self.uploaderId = existingUploaderRecords['objects'][0]['id']
            if 'settings' in existingUploaderRecords['objects'][0]:
                self.uploaderSettings = \
                    existingUploaderRecords['objects'][0]['settings']
                settingsUpdatedString = \
                    existingUploaderRecords['objects'][0]['settings_updated']
                logger.info(settingsUpdatedString)
                if settingsUpdatedString:
                    self.settingsUpdated = \
                        dateutil.parser.parse(settingsUpdatedString)
            else:
                self.uploaderSettings = None

        return self.uploaderSettings

    @staticmethod
    def GetActiveNetworkInterfaces():
        """
        Get active network interfaces
        """
        logger.debug("Determining the active network interface...")
        activeInterfaces = []
        if netifaces.AF_INET in netifaces.gateways()['default'].keys():
            activeInterfaces.append(
                netifaces.gateways()['default'][netifaces.AF_INET][1])
        return activeInterfaces

    def GenerateUuid(self):
        """
        Generate UUID
        """
        self.uuid = str(uuid.uuid1())
        logger.debug("Generated UUID: %s" % self.uuid)

    def GetUuid(self):
        """
        Get UUID
        """
        return self.uuid

    def SetUuid(self, uploaderUuid):
        """
        Set UUID
        """
        self.uuid = uploaderUuid

    def GetName(self):
        """
        Get uploader name
        """
        return self.name

    def GetHostname(self):
        """
        Get hostname
        """
        return self.hostname

    def GetSettingsUpdated(self):
        """
        Get the date at which settings were last updated on the server
        """
        return self.settingsUpdated


class UploaderRegistrationRequest(object):
    """
    Model class for MyTardis API v1's UploaderRegistrationRequestAppResource.
    See: https://github.com/mytardis/mytardis-app-mydata/blob/master/api.py
    """
    def __init__(self, settingsModel=None, uploaderRegRequestJson=None):
        self.settingsModel = settingsModel
        self.uploaderRegRequestJson = uploaderRegRequestJson

    def IsApproved(self):
        """
        Return True if uploader registration request has been approved
        """
        return self.uploaderRegRequestJson['approved']

    def GetApprovedStorageBox(self):
        """
        Return approved storage box
        """
        storageBoxJson = self.uploaderRegRequestJson['approved_storage_box']
        return StorageBox(storageBoxJson=storageBoxJson)

    def GetScpUsername(self):
        """
        Return 'scp_username' storage box attribute
        """
        storageBox = self.GetApprovedStorageBox()
        attributes = storageBox.GetAttributes()
        for attribute in attributes:
            if attribute.GetKey() == "scp_username":
                return attribute.GetValue()
        raise StorageBoxAttributeNotFound(storageBox, "scp_username")

    def GetScpHostname(self):
        """
        Return 'scp_hostname' storage box attribute
        """
        storageBox = self.GetApprovedStorageBox()
        attributes = storageBox.GetAttributes()
        for attribute in attributes:
            if attribute.GetKey() == "scp_hostname":
                return attribute.GetValue()
        raise StorageBoxAttributeNotFound(storageBox, "scp_hostname")

    def GetScpPort(self):
        """
        Return 'scp_port' storage box attribute
        """
        storageBox = self.GetApprovedStorageBox()
        attributes = storageBox.GetAttributes()
        for attribute in attributes:
            if attribute.GetKey() == "scp_port":
                return attribute.GetValue()
        return "22"

    def GetLocation(self):
        """
        Return 'location' storage box option
        """
        storageBox = self.GetApprovedStorageBox()
        options = storageBox.GetOptions()
        for option in options:
            if option.GetKey() == "location":
                return option.GetValue()
        raise StorageBoxOptionNotFound(storageBox, "location")

"""
mydata/models/uploader.py

The purpose of this module is to help with registering MyData uploaders
(which are usually instrument PCs) with the MyTardis server.

MyData POSTs some basic information about the PC and about the MyData
installation to its MyTardis server.  This basic information is called an
"Uploader" record.  In previous MyData versions, a single MyData user could
create multiple Uploader records from each PC they run MyData on, one for
each network interface on each PC.  In the latest MyData version however,
that the Uploader is made unique by a locally-generated UUID (instead of
the network interface's MAC address), each MyData instance should only
have one Uploader record in MyTardis.

Initially only HTTP POST uploads are enabled in MyData, but MyData will
request uploads via SCP to a staging area, and wait for a MyTardis
administrator to approve the request (which requires updating the
UploaderRegistrationRequest record created by MyData in the Djano Admin
interface).

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
$ usermod -a -G www-data mydata

N.B.: The test below was only possible because the MyData user submitting the
request and the MyTardis administrator approving the request were the same
person.  Normally, the MyTardis administrator wouldn't have access to the
MyData user's private key.

$ ssh -i ~/.ssh/MyData mydata@118.138.241.33
[mydata@118.138.241.33 ~]$ groups
mydata mytardis
[mydata@118.138.241.33 ~]$ ls -lh /var/lib/mytardis | grep receiving
drwxrws--- 8 mytardis www-data 4096 May 15 13:30 receiving
[mydata@118.138.241.33 ~]$ touch /var/lib/mytardis/receiving/test123.txt
[mydata@118.138.241.33 ~]$ ls -l /var/lib/mytardis/receiving/test123.txt
-rw-rw-r-- 1 mydata www-data 0 May 15 13:40 /var/lib/mytardis/receiving/test123.txt

Note the permissions above - being part of the "www-data" group on this staging
host allows the "mydata" user to write to the staging (receiving) directory, but
not to MyTardis's permanent storage location.

The 's' in the "receiving" directory's permissions (set with 'chmod g+s') is
important.  It means that files created within that directory by the "mydata"
user will have a default group of "www-data" (inherited from the "receiving"
directory), instead of having a default group of "mydata".
"""

# pylint: disable=missing-docstring

import requests
import json
import os
import psutil
import sys
import platform
import getpass
import subprocess
import re
import pkgutil
import urllib
import traceback
import uuid
import threading

from mydata import __version__ as VERSION
from mydata.models.storage import StorageBox
from mydata.logs import logger
import mydata.utils.openssh as OpenSSH
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import PrivateKeyDoesNotExist
from mydata.utils.exceptions import NoActiveNetworkInterface
from mydata.utils.exceptions import MissingMyDataAppOnMyTardisServer
from mydata.utils.exceptions import StorageBoxOptionNotFound
from mydata.utils.exceptions import StorageBoxAttributeNotFound
from mydata.utils import BytesToHuman


DEFAULT_STARTUP_INFO = None
DEFAULT_CREATION_FLAGS = 0
if sys.platform.startswith("win"):
    DEFAULT_STARTUP_INFO = subprocess.STARTUPINFO()
    # pylint: disable=protected-access
    DEFAULT_STARTUP_INFO.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
    DEFAULT_STARTUP_INFO.wShowWindow = subprocess.SW_HIDE
    # pylint: disable=import-error
    import win32process
    DEFAULT_CREATION_FLAGS = win32process.CREATE_NO_WINDOW


class UploaderModel(object):
    """
    Model class for MyTardis API v1's UploaderAppResource.
    See: https://github.com/wettenhj/mytardis-app-mydata/blob/master/api.py
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, settingsModel):
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        self.settingsModel = settingsModel
        self.interface = None
        self.responseJson = None

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

        # Here we check connectivity even if we've already done so, because
        # we need to ensure that we get the correct network interface for
        # self.interface, otherwise if the active interface changes,
        # we can get errors like this: KeyError: 'RTC'
        # when accessing things like ipv4Address[self.interface]

        activeInterfaces = UploaderModel.GetActiveNetworkInterfaces()
        if len(activeInterfaces) == 0:
            message = "No active network interfaces." \
                "\n\n" \
                "Please ensure that you have an active network interface " \
                "(e.g. Ethernet or WiFi)."
            raise NoActiveNetworkInterface(message)
        # Sometimes on Windows XP, you can end up with multiple results
        # from "netsh interface show interface"
        # If there is one called "Local Area Connection",
        # then that's the one we'll go with.
        if "Local Area Connection" in activeInterfaces:
            activeInterfaces = ["Local Area Connection"]
        elif "Local Area Connection 2" in activeInterfaces:
            activeInterfaces = ["Local Area Connection 2"]
        elif "Ethernet" in activeInterfaces:
            activeInterfaces = ["Ethernet"]
        elif "Wi-Fi" in activeInterfaces:
            activeInterfaces = ["Wi-Fi"]

        # For now, we're only dealing with one active network interface.
        # It is possible to have more than one active network interface,
        # but we hope that the code above has picked the best one.
        # If there are no active interfaces, then we shouldn't have
        # reached this point - we should have already raised an
        # exception.
        self.interface = activeInterfaces[0]

        if sys.platform.startswith("win"):
            proc = subprocess.Popen(["ipconfig", "/all"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=DEFAULT_STARTUP_INFO,
                                    creationflags=DEFAULT_CREATION_FLAGS)
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                raise Exception(stdout)

            macAddress = {}
            ipv4Address = {}
            ipv6Address = {}
            subnetMask = {}
            interface = ""

            for row in stdout.split("\n"):
                match = re.match(r"^\S.*adapter (.*):\s*$", row)
                if match:
                    interface = match.groups()[0]
                if interface == self.interface:
                    if ': ' in row:
                        key, value = row.split(': ')
                        if key.strip(' .') == "Physical Address":
                            macAddress[interface] = value.strip()
                        if "IPv4 Address" in key.strip(' .'):
                            ipv4Address[interface] = \
                                value.strip().replace("(Preferred)", "")
                        if "IPv6 Address" in key.strip(' .'):
                            ipv6Address[interface] = \
                                value.strip().replace("(Preferred)", "")
                        if "Subnet Mask" in key.strip(' .'):
                            subnetMask[interface] = value.strip()
        else:
            proc = subprocess.Popen(["ifconfig", self.interface],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=DEFAULT_STARTUP_INFO,
                                    creationflags=DEFAULT_CREATION_FLAGS)
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                raise Exception(stdout)

            macAddress = {}
            ipv4Address = {}
            ipv6Address = {}
            subnetMask = {}

            for row in stdout.split("\n"):
                match = re.match(r"\s+ether (\S*)\s*$", row)
                if match:
                    macAddress[self.interface] = match.groups()[0]
                match = re.match(r"\s+inet (\S*)\s+netmask\s+(\S*)\s+.*$", row)
                if match:
                    ipv4Address[self.interface] = match.groups()[0]
                    subnetMask[self.interface] = match.groups()[1]
                match = re.match(r"\s+inet6 (\S*)\s+.*$", row)
                if match:
                    ipv6Address[self.interface] = match.groups()[0]

        self.macAddress = macAddress[self.interface]
        if self.interface in ipv4Address:
            self.ipv4Address = ipv4Address[self.interface]
        else:
            self.ipv4Address = ""
        if self.interface in ipv6Address:
            self.ipv6Address = ipv6Address[self.interface]
        else:
            self.ipv6Address = ""
        if self.interface in subnetMask:
            self.subnetMask = subnetMask[self.interface]
        else:
            self.subnetMask = ""

        logger.info("The active network interface is: " + str(self.interface))

        self.name = self.settingsModel.GetInstrumentName()
        self.contactName = self.settingsModel.GetContactName()
        self.contactEmail = self.settingsModel.GetContactEmail()

        self.userAgentName = "MyData"
        self.userAgentVersion = VERSION
        self.userAgentInstallLocation = ""

        # pylint: disable=bare-except
        if hasattr(sys, 'frozen'):
            self.userAgentInstallLocation = os.path.dirname(sys.executable)
        else:
            try:
                self.userAgentInstallLocation = \
                    os.path.dirname(pkgutil.get_loader("MyData").filename)
            except:
                self.userAgentInstallLocation = os.getcwd()

        fmt = "%-17s %8s %8s %8s %5s%% %9s  %s\n"
        diskUsage = (fmt % ("Device", "Total", "Used", "Free", "Use ", "Type",
                            "Mount"))

        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt':
                if 'cdrom' in part.opts or part.fstype == '':
                    # skip cd-rom drives with no disk in it; they may raise
                    # ENOENT, pop-up a Windows GUI error for a non-ready
                    # partition or just hang.
                    continue
            usage = psutil.disk_usage(part.mountpoint)
            diskUsage = diskUsage + (fmt % (
                part.device,
                BytesToHuman(usage.total),
                BytesToHuman(usage.used),
                BytesToHuman(usage.free),
                int(usage.percent),
                part.fstype,
                part.mountpoint))

        self.diskUsage = diskUsage.strip()
        self.dataPath = self.settingsModel.GetDataDirectory()
        self.defaultUser = self.settingsModel.GetUsername()

    def UploadUploaderInfo(self):
        """ Uploads info about the instrument PC to MyTardis via HTTP POST """
        # pylint: disable=too-many-statements
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        myTardisUsername = self.settingsModel.GetUsername()
        myTardisApiKey = self.settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/mydata_uploader/?format=json" + \
            "&uuid=" + urllib.quote(self.uuid)
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey),
            "Content-Type": "application/json",
            "Accept": "application/json"}

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
        existingUploaderRecords = response.json()
        numExistingUploaderRecords = \
            existingUploaderRecords['meta']['total_count']
        if numExistingUploaderRecords > 0:
            uploaderId = existingUploaderRecords['objects'][0]['id']

        logger.info("Uploading uploader info to MyTardis...")

        if numExistingUploaderRecords > 0:
            url = myTardisUrl + "/api/v1/mydata_uploader/%d/" % uploaderId
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
        if numExistingUploaderRecords > 0:
            response = requests.put(headers=headers, url=url, data=data)
        else:
            response = requests.post(headers=headers, url=url, data=data)
        if response.status_code >= 200 and response.status_code < 300:
            logger.info("Upload succeeded for uploader info.")
            self.responseJson = response.json()
        else:
            logger.error("Upload failed for uploader info.")
            logger.error("Status code = " + str(response.status_code))
            logger.error(response.text)
            raise Exception(response.text)

    def ExistingUploadToStagingRequest(self):
        try:
            # The private key file path must be ~/.ssh/MyData
            keyPair = OpenSSH.FindKeyPair("MyData")
        except PrivateKeyDoesNotExist:
            keyPair = OpenSSH.NewKeyPair("MyData")
        self.settingsModel.SetSshKeyPair(keyPair)
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        myTardisUsername = self.settingsModel.GetUsername()
        myTardisApiKey = self.settingsModel.GetApiKey()
        url = myTardisUrl + \
            "/api/v1/mydata_uploaderregistrationrequest/?format=json" + \
            "&uploader__uuid=" + self.uuid + \
            "&requester_key_fingerprint=" + \
            urllib.quote(keyPair.GetFingerprint())
        logger.debug(url)
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey),
            "Content-Type": "application/json",
            "Accept": "application/json"}
        response = requests.get(headers=headers, url=url)
        if response.status_code < 200 or response.status_code >= 300:
            if response.status_code == 404:
                response.close()
                raise DoesNotExist("HTTP 404 (Not Found) received for: " + url)
            message = response.text
            response.close()
            raise Exception(message)
        logger.debug(response.text)
        existingUploaderRecords = response.json()
        numExistingUploaderRecords = \
            existingUploaderRecords['meta']['total_count']
        if numExistingUploaderRecords > 0:
            approvalJson = existingUploaderRecords['objects'][0]
            logger.info("A request already exists for this uploader.")
            response.close()
            return UploaderRegistrationRequest(
                settingsModel=self.settingsModel,
                uploaderRegRequestJson=approvalJson)
        else:
            message = "This uploader hasn't requested uploading " \
                      "via staging yet."
            logger.info(message)
            response.close()
            raise DoesNotExist(message)

    def RequestUploadToStagingApproval(self):
        """
        Used to request the ability to upload via SCP
        to a staging area, and then register in MyTardis.
        """
        try:
            keyPair = OpenSSH.FindKeyPair("MyData")
        except PrivateKeyDoesNotExist:
            keyPair = OpenSSH.NewKeyPair("MyData")
        self.settingsModel.SetSshKeyPair(keyPair)
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        myTardisUsername = self.settingsModel.GetUsername()
        myTardisApiKey = self.settingsModel.GetApiKey()
        url = myTardisUrl + "/api/v1/mydata_uploaderregistrationrequest/"
        headers = {
            "Authorization": "ApiKey %s:%s" % (myTardisUsername,
                                               myTardisApiKey),
            "Content-Type": "application/json",
            "Accept": "application/json"}
        uploaderRegistrationRequestJson = \
            {"uploader": self.responseJson['resource_uri'],
             "name": self.name,
             "requester_name": self.contactName,
             "requester_email": self.contactEmail,
             "requester_public_key": keyPair.GetPublicKey(),
             "requester_key_fingerprint": keyPair.GetFingerprint()}
        data = json.dumps(uploaderRegistrationRequestJson)
        response = requests.post(headers=headers, url=url, data=data)
        if response.status_code >= 200 and response.status_code < 300:
            responseJson = response.json()
            response.close()
            return UploaderRegistrationRequest(
                settingsModel=self.settingsModel,
                uploaderRegRequestJson=responseJson)
        else:
            if response.status_code == 404:
                response.close()
                raise DoesNotExist("HTTP 404 (Not Found) received for: " + url)
            logger.error("Status code = " + str(response.status_code))
            logger.error("URL = " + url)
            message = response.text
            response.close()
            raise Exception(message)

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
                    print traceback.format_exc()
                    logger.error(traceback.format_exc())
                    raise
                uploadToStagingRequest = None
                try:
                    uploadToStagingRequest = \
                        self.ExistingUploadToStagingRequest()
                except DoesNotExist:
                    uploadToStagingRequest = \
                        self.RequestUploadToStagingApproval()
                    logger.info("Uploader registration request created.")
                except PrivateKeyDoesNotExist:
                    logger.info("Generating new uploader registration request, "
                                "because private key was moved or deleted.")
                    uploadToStagingRequest = \
                        self.RequestUploadToStagingApproval()
                    logger.info("Generated new uploader registration request, "
                                "because private key was moved or deleted.")
                if uploadToStagingRequest.IsApproved():
                    logger.info("Uploads to staging have been approved!")
                else:
                    logger.info("Uploads to staging haven't been approved yet.")
                self.settingsModel\
                    .SetUploadToStagingRequest(uploadToStagingRequest)
            except:
                logger.error(traceback.format_exc())
                raise
            finally:
                self.requestStagingAccessThreadLock.release()

    @staticmethod
    def GetActiveNetworkInterfaces():
        # pylint: disable=too-many-branches
        logger.info("Determining the active network interface...")
        activeInterfaces = []
        if sys.platform.startswith("win"):
            proc = subprocess.Popen(["netsh", "interface",
                                     "show", "interface"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=DEFAULT_STARTUP_INFO,
                                    creationflags=DEFAULT_CREATION_FLAGS)
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                raise Exception(stdout)

            for row in stdout.split("\n"):
                match = re.match(r"^(Enabled|Disabled)\s*(Connected|Disconnected)"
                                 r"\s*(Dedicated|Internal|Loopback)\s*(.*)\s*$",
                                 row)
                if match:
                    adminState = match.groups()[0]
                    state = match.groups()[1]
                    interfaceType = match.groups()[2]
                    interface = match.groups()[3].strip()
                    if adminState == "Enabled" and state == "Connected" \
                            and interfaceType == "Dedicated":
                        activeInterfaces.append(interface)
                # On Windows XP, the state may be blank:
                match = re.match(r"^(Enabled|Disabled)\s*"
                                 r"(Dedicated|Internal|Loopback)\s*(.*)\s*$", row)
                if match:
                    adminState = match.groups()[0]
                    interfaceType = match.groups()[1]
                    interface = match.groups()[2].strip()
                    if adminState == "Enabled" and \
                            interfaceType == "Dedicated":
                        activeInterfaces.append(interface)
        elif sys.platform.startswith("darwin"):
            # Was using "route get default" here, but for VPN, that can
            # return "utun0" which doesn't have a corresponding MAC address,
            # and there may be other missing network-related fields in the
            # ifconfig entry for "utun0".  For now, we will instead find
            # the physical network device which is active, but in future
            # we can relax the requirement of needing the MAC address etc.
            # because we are now using a UUID as our Uploader record's
            # unique identifier instead of a MAC address.
            proc = subprocess.Popen(["ifconfig"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=DEFAULT_STARTUP_INFO,
                                    creationflags=DEFAULT_CREATION_FLAGS)
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                raise Exception(stdout)

            currentInterface = None
            for line in stdout.split("\n"):
                match = re.match(r"^(\S+): flags=.*", line)
                if match:
                    currentInterface = match.groups()[0].strip()
                match = re.match(r"^\s+status: active", line)
                if match and currentInterface:
                    activeInterfaces.append(currentInterface)
        elif sys.platform.startswith("linux"):
            proc = subprocess.Popen(["route"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=DEFAULT_STARTUP_INFO,
                                    creationflags=DEFAULT_CREATION_FLAGS)
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                raise Exception(stdout)

            for line in stdout.split("\n"):
                match = re.match(r"^default.*\s+(\S+)\s*$", line)
                if match:
                    interface = match.groups()[0].strip()
                    activeInterfaces.append(interface)

        return activeInterfaces

    def GetSettingsModel(self):
        return self.settingsModel

    def SetSettingsModel(self, settingsModel):
        self.settingsModel = settingsModel

    def GenerateUuid(self):
        self.uuid = str(uuid.uuid1())
        logger.debug("Generated UUID: %s" % self.uuid)

    def GetUuid(self):
        return self.uuid

    def GetName(self):
        return self.name

    def GetHostname(self):
        return self.hostname


class UploaderRegistrationRequest(object):
    """
    Model class for MyTardis API v1's UploaderRegistrationRequestAppResource.
    See: https://github.com/wettenhj/mytardis-app-mydata/blob/master/api.py
    """
    def __init__(self, settingsModel=None, uploaderRegRequestJson=None):
        self.settingsModel = settingsModel
        self.uploaderRegRequestJson = uploaderRegRequestJson

    def GetJson(self):
        return self.uploaderRegRequestJson

    def IsApproved(self):
        return self.uploaderRegRequestJson['approved']

    def GetApprovedStorageBox(self):
        storageBoxJson = self.uploaderRegRequestJson['approved_storage_box']
        return StorageBox(storageBoxJson=storageBoxJson)

    def GetScpUsername(self):
        storageBox = self.GetApprovedStorageBox()
        attributes = storageBox.GetAttributes()
        for attribute in attributes:
            if attribute.GetKey() == "scp_username":
                return attribute.GetValue()
        raise StorageBoxAttributeNotFound(storageBox, "scp_username")

    def GetScpHostname(self):
        storageBox = self.GetApprovedStorageBox()
        attributes = storageBox.GetAttributes()
        for attribute in attributes:
            if attribute.GetKey() == "scp_hostname":
                return attribute.GetValue()
        raise StorageBoxAttributeNotFound(storageBox, "scp_hostname")

    def GetLocation(self):
        storageBox = self.GetApprovedStorageBox()
        options = storageBox.GetOptions()
        for option in options:
            if option.GetKey() == "location":
                return option.GetValue()
        raise StorageBoxOptionNotFound(storageBox, "location")

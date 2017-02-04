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
host allows the "mydata" user to write to the staging (receiving) directory, but
not to MyTardis's permanent storage location.

The 's' in the "receiving" directory's permissions (set with 'chmod g+s') is
important.  It means that files created within that directory by the "mydata"
user will have a default group of "mytardis" (inherited from the "receiving"
directory), instead of having a default group of "mydata".
"""

# pylint: disable=missing-docstring
# pylint: disable=wrong-import-position

import json
import os
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

import dateutil.parser
import psutil
import requests

if sys.platform.startswith("win"):
    # pylint: disable=import-error
    import win32process

if sys.platform.startswith("linux"):
    # pylint: disable=import-error
    import netifaces

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
    DEFAULT_CREATION_FLAGS = win32process.CREATE_NO_WINDOW  # pylint: disable=no-member

DEFAULT_TIMEOUT = 3


class UploaderModel(object):
    """
    Model class for MyTardis API v1's UploaderAppResource.
    See: https://github.com/mytardis/mytardis-app-mydata/blob/master/api.py
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, settingsModel):
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        self.settingsModel = settingsModel
        self.interface = None
        self.responseJson = None

        self.id = None  # pylint: disable=invalid-name
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
        elif "Internet" in activeInterfaces:
            activeInterfaces = ["Internet"]
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
                            ipv4Address[interface] = \
                                ipv4Address[interface] \
                                    .replace("(Tentative)", "")
                        if "IPv6 Address" in key.strip(' .'):
                            ipv6Address[interface] = \
                                value.strip().replace("(Preferred)", "")
                            ipv6Address[interface] = \
                                ipv6Address[interface] \
                                    .replace("(Tentative)", "")
                        if "Subnet Mask" in key.strip(' .'):
                            subnetMask[interface] = value.strip()
        elif sys.platform.startswith("darwin"):
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
                if sys.platform.startswith("darwin"):
                    match = re.match(r"\s+ether (\S*)\s*$", row)
                else:
                    match = re.match(r".*\s+HWaddr (\S*)\s*$", row)
                if match:
                    macAddress[self.interface] = match.groups()[0]
                match = re.match(r"\s+inet (\S*)\s+netmask\s+(\S*)\s+.*$", row)
                if match:
                    ipv4Address[self.interface] = match.groups()[0]
                    subnetMask[self.interface] = match.groups()[1]
                match = re.match(r"\s+inet6 (\S*)\s+.*$", row)
                if match:
                    ipv6Address[self.interface] = match.groups()[0]
        else:
            macAddress = {}
            ipv4Address = {}
            ipv6Address = {}
            subnetMask = {}
            interface = self.interface

            macAddress[interface] = \
                netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']

            ipv4Addrs = netifaces.ifaddresses(interface)[netifaces.AF_INET]
            ipv4Address[interface] = ipv4Addrs[0]['addr']
            subnetMask[interface] = ipv4Addrs[0]['netmask']

            ipv6Addrs = netifaces.ifaddresses(interface)[netifaces.AF_INET6]
            for addr in ipv6Addrs:
                match = re.match(r'(.+)%(.+)', addr['addr'])
                if match and match.group(2) == interface:
                    ipv6Address[interface] = match.group(1)

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

        logger.debug("The active network interface is: " + str(self.interface))

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
            logger.error("An error occurred while retrieving uploader info.")
            logger.error("Status code = " + str(response.status_code))
            logger.error(response.text)
            raise Exception(response.text)
        numExistingUploaderRecords = \
            existingUploaderRecords['meta']['total_count']
        if numExistingUploaderRecords > 0:
            self.id = existingUploaderRecords['objects'][0]['id']
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
            url = myTardisUrl + "/api/v1/mydata_uploader/%d/" % self.id
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
            logger.error("Upload failed for uploader info.")
            logger.error("Status code = " + str(response.status_code))
            logger.error(response.text)
            raise Exception(response.text)

    def ExistingUploadToStagingRequest(self):
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
            logger.debug("A request already exists for this uploader.")
            response.close()
            return UploaderRegistrationRequest(
                settingsModel=self.settingsModel,
                uploaderRegRequestJson=approvalJson)
        else:
            message = "This uploader hasn't requested uploading " \
                      "via staging yet."
            logger.debug(message)
            response.close()
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
                    logger.debug("Generating new uploader registration request, "
                                 "because private key was moved or deleted.")
                    uploadToStagingRequest = \
                        self.RequestUploadToStagingApproval()
                    logger.debug("Generated new uploader registration request, "
                                 "because private key was moved or deleted.")
                if uploadToStagingRequest.IsApproved():
                    logger.debug("Uploads to staging have been approved!")
                else:
                    logger.debug("Uploads to staging haven't been approved yet.")
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

        if not self.id:
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
                logger.error("An error occurred while retrieving uploader id.")
                logger.error("Status code = " + str(response.status_code))
                logger.error(response.text)
                raise Exception(response.text)
            numExistingUploaderRecords = \
                existingUploaderRecords['meta']['total_count']
            if numExistingUploaderRecords > 0:
                self.id = existingUploaderRecords['objects'][0]['id']
            else:
                logger.debug("Uploader record doesn't exist yet, so "
                             "we can't save settings to the server.")
                return

        url = "%s/api/v1/mydata_uploader/%s/" % (myTardisUrl, self.id)

        patchData = {
            'settings': settingsList,
            'uuid': self.uuid
        }
        response = requests.patch(headers=headers, url=url,
                                  data=json.dumps(patchData))
        if response.status_code != 202:
            logger.error(url)
            message = response.text
            logger.error(message)
            raise Exception(message)

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
            logger.error("An error occurred while retrieving uploader.")
            logger.error("Status code = " + str(response.status_code))
            logger.error(response.text)
            raise Exception(response.text)
        numExistingUploaderRecords = \
            existingUploaderRecords['meta']['total_count']
        if numExistingUploaderRecords > 0:
            if 'id' in existingUploaderRecords['objects'][0]:
                self.id = existingUploaderRecords['objects'][0]['id']
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
        # pylint: disable=too-many-branches
        logger.debug("Determining the active network interface...")
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
            interface = netifaces.gateways()['default'][netifaces.AF_INET][1]
            activeInterfaces.append(interface)

        return activeInterfaces

    def GenerateUuid(self):
        self.uuid = str(uuid.uuid1())
        logger.debug("Generated UUID: %s" % self.uuid)

    def GetUuid(self):
        return self.uuid

    def SetUuid(self, uploaderUuid):
        self.uuid = uploaderUuid

    def GetName(self):
        return self.name

    def GetHostname(self):
        return self.hostname

    def GetSettingsUpdated(self):
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

    def GetScpPort(self):
        storageBox = self.GetApprovedStorageBox()
        attributes = storageBox.GetAttributes()
        for attribute in attributes:
            if attribute.GetKey() == "scp_port":
                return attribute.GetValue()
        return "22"

    def GetLocation(self):
        storageBox = self.GetApprovedStorageBox()
        options = storageBox.GetOptions()
        for option in options:
            if option.GetKey() == "location":
                return option.GetValue()
        raise StorageBoxOptionNotFound(storageBox, "location")

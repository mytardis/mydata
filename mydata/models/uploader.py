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
from datetime import datetime
import wx
import uuid

from mydata import __version__ as VERSION
from mydata.models.storage import StorageBox
from mydata.logging import logger
import mydata.utils.openssh as OpenSSH
from mydata.utils.exceptions import DoesNotExist
from mydata.utils.exceptions import PrivateKeyDoesNotExist
from mydata.utils.exceptions import NoActiveNetworkInterface
from mydata.utils.exceptions import StringTooLongForField
from mydata.utils.exceptions import MissingMyDataAppOnMyTardisServer
from mydata.utils.exceptions import StorageBoxOptionNotFound
from mydata.utils.exceptions import StorageBoxAttributeNotFound


defaultStartupInfo = None
defaultCreationFlags = 0
if sys.platform.startswith("win"):
    defaultStartupInfo = subprocess.STARTUPINFO()
    defaultStartupInfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
    defaultStartupInfo.wShowWindow = subprocess.SW_HIDE
    import win32process
    defaultCreationFlags = win32process.CREATE_NO_WINDOW


class UploaderModel():
    def __init__(self, settingsModel):
        self.settingsModel = settingsModel
        self.interface = None
        self.responseJson = None

        self.uuid = self.settingsModel.GetUuid()
        if self.uuid is None:
            self.GenerateUuid()
            self.settingsModel.SetUuid(self.uuid)

        intervalSinceLastConnectivityCheck = \
            datetime.now() - wx.GetApp().GetLastNetworkConnectivityCheckTime()

        # Here we check connectivity even if we've already done so, because
        # we need to ensure that we get the correct network interface for
        # self.interface, otherwise if the active interface changes,
        # we can get errors like this: KeyError: 'RTC'
        # when accessing things like ipv4_address[self.interface]

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
                                    startupinfo=defaultStartupInfo,
                                    creationflags=defaultCreationFlags)
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                raise Exception(stdout)

            mac_address = {}
            ipv4_address = {}
            ipv6_address = {}
            subnet_mask = {}
            interface = ""

            for row in stdout.split("\n"):
                m = re.match(r"^\S.*adapter (.*):\s*$", row)
                if m:
                    interface = m.groups()[0]
                if interface == self.interface:
                    if ': ' in row:
                        key, value = row.split(': ')
                        if key.strip(' .') == "Physical Address":
                            mac_address[interface] = value.strip()
                        if "IPv4 Address" in key.strip(' .'):
                            ipv4_address[interface] = \
                                value.strip().replace("(Preferred)", "")
                        if "IPv6 Address" in key.strip(' .'):
                            ipv6_address[interface] = \
                                value.strip().replace("(Preferred)", "")
                        if "Subnet Mask" in key.strip(' .'):
                            subnet_mask[interface] = value.strip()
        else:
            proc = subprocess.Popen(["ifconfig", self.interface],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=defaultStartupInfo,
                                    creationflags=defaultCreationFlags)
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                raise Exception(stdout)

            mac_address = {}
            ipv4_address = {}
            ipv6_address = {}
            subnet_mask = {}

            for row in stdout.split("\n"):
                m = re.match(r"\s+ether (\S*)\s*$", row)
                if m:
                    mac_address[self.interface] = m.groups()[0]
                m = re.match(r"\s+inet (\S*)\s+netmask\s+(\S*)\s+.*$", row)
                if m:
                    ipv4_address[self.interface] = m.groups()[0]
                    subnet_mask[self.interface] = m.groups()[1]
                m = re.match(r"\s+inet6 (\S*)\s+.*$", row)
                if m:
                    ipv6_address[self.interface] = m.groups()[0]

        self.mac_address = mac_address[self.interface]
        if self.interface in ipv4_address:
            self.ipv4_address = ipv4_address[self.interface]
        else:
            self.ipv4_address = ""
        if self.interface in ipv6_address:
            self.ipv6_address = ipv6_address[self.interface]
        else:
            self.ipv6_address = ""
        if self.interface in subnet_mask:
            self.subnet_mask = subnet_mask[self.interface]
        else:
            self.subnet_mask = ""

        logger.info("The active network interface is: " + str(self.interface))

        self.name = self.settingsModel.GetInstrumentName()
        self.contact_name = self.settingsModel.GetContactName()
        self.contact_email = self.settingsModel.GetContactEmail()

        self.user_agent_name = "MyData"
        self.user_agent_version = VERSION
        self.user_agent_install_location = ""

        if hasattr(sys, 'frozen'):
            self.user_agent_install_location = os.path.dirname(sys.executable)
        else:
            try:
                self.user_agent_install_location = \
                    os.path.dirname(pkgutil.get_loader("MyData").filename)
            except:
                self.user_agent_install_location = os.getcwd()

        fmt = "%-17s %8s %8s %8s %5s%% %9s  %s\n"
        disk_usage = (fmt % ("Device", "Total", "Used", "Free", "Use ", "Type",
                             "Mount"))

        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt':
                if 'cdrom' in part.opts or part.fstype == '':
                    # skip cd-rom drives with no disk in it; they may raise
                    # ENOENT, pop-up a Windows GUI error for a non-ready
                    # partition or just hang.
                    continue
            usage = psutil.disk_usage(part.mountpoint)
            disk_usage = disk_usage + (fmt % (
                part.device,
                self._bytes2human(usage.total),
                self._bytes2human(usage.used),
                self._bytes2human(usage.free),
                int(usage.percent),
                part.fstype,
                part.mountpoint))

        self.disk_usage = disk_usage.strip()
        self.data_path = self.settingsModel.GetDataDirectory()
        self.default_user = self.settingsModel.GetUsername()

    def _bytes2human(self, n):
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i + 1) * 10
        for s in reversed(symbols):
            if n >= prefix[s]:
                value = float(n) / prefix[s]
                return '%.1f%s' % (value, s)
        return "%sB" % n

    def UploadUploaderInfo(self):
        """ Uploads info about the instrument PC to MyTardis via HTTP POST """
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = self.settingsModel.GetUsername()
        myTardisDefaultUserApiKey = self.settingsModel.GetApiKey()

        url = myTardisUrl + "/api/v1/mydata_uploader/?format=json" + \
            "&uuid=" + urllib.quote(self.uuid)

        headers = {"Authorization": "ApiKey " + myTardisDefaultUsername + ":" +
                   myTardisDefaultUserApiKey,
                   "Content-Type": "application/json",
                   "Accept": "application/json"}

        try:
            response = requests.get(headers=headers, url=url)
        except Exception, e:
            logger.error(str(e))
            raise
        if response.status_code == 404:
            message = "The MyData app is missing from the MyTardis server."
            logger.error(url)
            logger.error(message)
            raise MissingMyDataAppOnMyTardisServer(message)
        existingMatchingUploaderRecords = response.json()
        numExistingMatchingUploaderRecords = \
            existingMatchingUploaderRecords['meta']['total_count']
        if numExistingMatchingUploaderRecords > 0:
            uploader_id = existingMatchingUploaderRecords['objects'][0]['id']

        logger.info("Uploading uploader info to MyTardis...")

        if numExistingMatchingUploaderRecords > 0:
            url = myTardisUrl + "/api/v1/mydata_uploader/%d/" % (uploader_id)
        else:
            url = myTardisUrl + "/api/v1/mydata_uploader/"

        self.os_platform = sys.platform
        self.os_system = platform.system()
        self.os_release = platform.release()
        self.os_version = platform.version()
        self.os_username = getpass.getuser()

        self.machine = platform.machine()
        self.architecture = str(platform.architecture())
        self.processor = platform.processor()
        self.memory = self._bytes2human(psutil.virtual_memory().total)
        self.cpus = psutil.cpu_count()

        self.hostname = platform.node()

        uploaderFieldLength = {
            "name": 64, "contact_name": 64, "contact_email": 64,
            "user_agent_name": 64, "user_agent_version": 32,
            "user_agent_install_location": 128,
            "os_platform": 64, "os_system": 64, "os_release": 32,
            "os_version": 128, "os_username": 64,
            "machine": 64, "architecture": 64, "processor": 64, "memory": 32,
            "data_path": 64, "default_user": 64,
            "interface": 64, "mac_address": 64, "ipv4_address": 16,
            "ipv6_address": 64, "subnet_mask": 16, "hostname": 64,
            "uuid": 36}

        for field in uploaderFieldLength:
            if len(getattr(self, field)) > uploaderFieldLength[field]:
                raise StringTooLongForField("Uploader", field,
                                            uploaderFieldLength[field],
                                            getattr(self, field))

        uploaderJson = {"uuid": self.uuid,
                        "name": self.name,
                        "contact_name": self.contact_name,
                        "contact_email": self.contact_email,

                        "user_agent_name": self.user_agent_name,
                        "user_agent_version": self.user_agent_version,
                        "user_agent_install_location":
                            self.user_agent_install_location,

                        "os_platform": self.os_platform,
                        "os_system": self.os_system,
                        "os_release": self.os_release,
                        "os_version": self.os_version,
                        "os_username": self.os_username,

                        "machine": self.machine,
                        "architecture": self.architecture,
                        "processor": self.processor,
                        "memory": self.memory,
                        "cpus": self.cpus,

                        "disk_usage": self.disk_usage,
                        "data_path": self.data_path,
                        "default_user": self.default_user,

                        "interface": self.interface,
                        "mac_address": self.mac_address,
                        "ipv4_address": self.ipv4_address,
                        "ipv6_address": self.ipv6_address,
                        "subnet_mask": self.subnet_mask,

                        "hostname": self.hostname,

                        "instruments": [self.settingsModel.GetInstrument()
                                        .GetResourceUri()]}

        data = json.dumps(uploaderJson, indent=4)
        logger.debug(data)
        if numExistingMatchingUploaderRecords > 0:
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
            # FIXME: For now, the private key file path has to be ~/.ssh/MyData
            keyPair = OpenSSH.FindKeyPair("MyData")
        except PrivateKeyDoesNotExist:
            keyPair = OpenSSH.NewKeyPair("MyData")
        self.settingsModel.SetSshKeyPair(keyPair)
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = self.settingsModel.GetUsername()
        myTardisDefaultUserApiKey = self.settingsModel.GetApiKey()
        url = myTardisUrl + \
            "/api/v1/mydata_uploaderregistrationrequest/?format=json" + \
            "&uploader__uuid=" + self.uuid + \
            "&requester_key_fingerprint=" + \
            urllib.quote(keyPair.GetFingerprint())
        logger.debug(url)
        headers = {"Authorization": "ApiKey " + myTardisDefaultUsername + ":" +
                   myTardisDefaultUserApiKey,
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
        existingMatchingUploaderRecords = response.json()
        numExistingMatchingUploaderRecords = \
            existingMatchingUploaderRecords['meta']['total_count']
        if numExistingMatchingUploaderRecords > 0:
            approval_json = existingMatchingUploaderRecords['objects'][0]
            logger.info("A request already exists for this uploader.")
            response.close()
            return UploaderRegistrationRequest(
                settingsModel=self.settingsModel, json=approval_json)
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
        myTardisDefaultUsername = self.settingsModel.GetUsername()
        myTardisDefaultUserApiKey = self.settingsModel.GetApiKey()
        url = myTardisUrl + "/api/v1/mydata_uploaderregistrationrequest/"
        headers = {"Authorization": "ApiKey " + myTardisDefaultUsername + ":" +
                   myTardisDefaultUserApiKey,
                   "Content-Type": "application/json",
                   "Accept": "application/json"}
        uploaderRegistrationRequestJson = \
            {"uploader": self.responseJson['resource_uri'],
             "name": self.name,
             "requester_name": self.contact_name,
             "requester_email": self.contact_email,
             "requester_public_key": keyPair.GetPublicKey(),
             "requester_key_fingerprint": keyPair.GetFingerprint()}
        data = json.dumps(uploaderRegistrationRequestJson)
        response = requests.post(headers=headers, url=url, data=data)
        if response.status_code >= 200 and response.status_code < 300:
            responseJson = response.json()
            response.close()
            return UploaderRegistrationRequest(
                settingsModel=self.settingsModel, json=responseJson)
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
        try:
            try:
                self.UploadUploaderInfo()
            except:
                print traceback.format_exc()
                logger.error(traceback.format_exc())
                raise
            uploadToStagingRequest = None
            try:
                uploadToStagingRequest = self.ExistingUploadToStagingRequest()
            except DoesNotExist:
                uploadToStagingRequest = self.RequestUploadToStagingApproval()
                logger.info("Uploader registration request created.")
            except PrivateKeyDoesNotExist:
                logger.info("Generating new uploader registration request, "
                            "because private key was moved or deleted.")
                uploadToStagingRequest = self.RequestUploadToStagingApproval()
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

    @staticmethod
    def GetActiveNetworkInterfaces():
        logger.info("Determining the active network interface...")
        activeInterfaces = []
        if sys.platform.startswith("win"):
            proc = subprocess.Popen(["netsh", "interface",
                                     "show", "interface"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=defaultStartupInfo,
                                    creationflags=defaultCreationFlags)
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                raise Exception(stdout)

            for row in stdout.split("\n"):
                m = re.match(r"^(Enabled|Disabled)\s*(Connected|Disconnected)"
                             "\s*(Dedicated|Internal|Loopback)\s*(.*)\s*$",
                             row)
                if m:
                    adminState = m.groups()[0]
                    state = m.groups()[1]
                    interfaceType = m.groups()[2]
                    interface = m.groups()[3].strip()
                    if adminState == "Enabled" and state == "Connected" \
                            and interfaceType == "Dedicated":
                        activeInterfaces.append(interface)
                # On Windows XP, the state may be blank:
                m = re.match(r"^(Enabled|Disabled)\s*"
                             "(Dedicated|Internal|Loopback)\s*(.*)\s*$", row)
                if m:
                    adminState = m.groups()[0]
                    interfaceType = m.groups()[1]
                    interface = m.groups()[2].strip()
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
                                    startupinfo=defaultStartupInfo,
                                    creationflags=defaultCreationFlags)
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                raise Exception(stdout)

            currentInterface = None
            for line in stdout.split("\n"):
                m = re.match(r"^(\S+): flags=.*", line)
                if m:
                    currentInterface = m.groups()[0].strip()
                m = re.match(r"^\s+status: active", line)
                if m and currentInterface:
                    activeInterfaces.append(currentInterface)
        elif sys.platform.startswith("linux"):
            proc = subprocess.Popen(["route"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=defaultStartupInfo,
                                    creationflags=defaultCreationFlags)
            stdout, _ = proc.communicate()
            if proc.returncode != 0:
                raise Exception(stdout)

            for line in stdout.split("\n"):
                m = re.match(r"^default.*\s+(\S+)\s*$", line)
                if m:
                    interface = m.groups()[0].strip()
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


class UploaderRegistrationRequest():
    def __init__(self, settingsModel=None, json=None):
        self.settingsModel = settingsModel
        self.json = json

    def GetJson(self):
        return self.json

    def IsApproved(self):
        return self.json['approved']

    def GetApprovedStorageBox(self):
        return StorageBox(storageBoxJson=self.json['approved_storage_box'])

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

"""
UploaderModel.py

The purpose of this module is to help with registering MyData uploaders
(which are usually instrument PCs) with the MyTardis server.

Every time MyData runs, or when its settings are updated, it POSTs to its
preferred MyTardis server some basic information about the PC and about the
MyData installation.  This basic information is called an "uploader" record.
This initial POST doesn't require any authentication, but once an uploader
record has been created in MyTardis, then no other users (of MyTardis's
RESTful API) will be able to access the uploader record unless they know
its MAC address, a unique string associated with the MyData user's network
interface (Ethernet or WiFi or ...).  A single MyData user could create
multiple uploader records from each PC they run MyData on, one for each
network interface on each PC.  The primary reason for allowing the initial
POST without authentication is because (at least for now), the MyTardis
administrators are keen to be notified of any users attempting to use
MyData, even if those users can't figure out how to configure
authentication in MyData.

Initially only HTTP POST uploads are enabled in MyData, but MyData will request
uploads via "cat >>" over SSH to a staging area, and wait for a MyTardis
administrator to approve the request.  Below is a sample of a MyTardis
administrator's notes made (in the approval_comments field in MyTardis's
UploadRegistrationRequest model) when approving one of these upload requests:

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

Then I tested SSHing into the staging host from my MyData test machine using
the SSH private key which MyData generated in ~/.ssh/:

$ ssh -i ~/.ssh/MyData mydata@118.138.241.33
[mydata@118.138.241.33 ~]$ groups
mydata mytardis
[mydata@118.138.241.33 ~]$ ls -lh /mnt/sonas/market | grep MYTARDIS
drwx------ 403 mytardis www-data 128K Nov 12 14:33 MYTARDIS_FILE_STORE
drwxrwx---   3 mytardis www-data  32K Nov 13 15:36 MYTARDIS_STAGING
[mydata@118.138.241.33 ~]$ touch /mnt/sonas/market/MYTARDIS_STAGING/test123.txt
[mydata@118.138.241.33 ~]$ rm /mnt/sonas/market/MYTARDIS_STAGING/test123.txt

Note the permissions above - being part of the "mytardis" group on this staging
host allows the "mydata" user to write to the MYTARDIS_STAGING directory, but
not to the MYTARDIS_FILE_STORE directory.
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

import MyDataVersionNumber
from logger.Logger import logger
import OpenSSH
from Exceptions import DoesNotExist
from Exceptions import PrivateKeyDoesNotExist
from Exceptions import NoActiveNetworkInterface


class UploaderModel():
    def __init__(self, settingsModel):
        self.settingsModel = settingsModel
        self.interface = None
        self.json = None

        activeInterfaces = self.GetActiveNetworkInterfaces()
        if len(activeInterfaces) == 0:
            message = "No active network interfaces." \
                "\n\n" \
                "Please ensure that you have an active network interface " \
                "(e.g. Ethernet or WiFi)."
            raise NoActiveNetworkInterface(message)
        # Sometimes on Windows XP, you can end up with multiple results from
        # "netsh interface show interface"
        # If there is one called "Local Area Connection",
        # then that's the one we'll go with.
        if "Local Area Connection" in activeInterfaces:
            activeInterfaces = ["Local Area Connection"]
        elif "Local Area Connection 2" in activeInterfaces:
            activeInterfaces = ["Local Area Connection 2"]

        # FIXME: ipconfig only works on Windows.
        # Need to add equivalent ifconfig command on Mac, Linux.
        proc = subprocess.Popen(["ipconfig", "/all"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = proc.communicate()
        if stderr is not None and stderr != "":
            logger.error(stderr)

        mac_address = {}
        ipv4_address = {}
        ipv6_address = {}
        subnet_mask = {}
        interface = ""

        for row in stdout.split("\n"):
            m = re.match(r"^\S.*adapter (.*):\s*$", row)
            if m:
                interface = m.groups()[0]
            if interface in activeInterfaces:
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

        self.interface = activeInterfaces[0]
        self.mac_address = mac_address[self.interface]
        self.ipv4_address = ipv4_address[self.interface]
        self.ipv6_address = ipv6_address[self.interface]
        self.subnet_mask = subnet_mask[self.interface]

        logger.info("The active network interface is: " + str(self.interface))

        self.name = self.settingsModel.GetInstrumentName()
        self.contact_name = self.settingsModel.GetContactName()
        self.contact_email = self.settingsModel.GetContactEmail()

        self.user_agent_name = "MyData"
        self.user_agent_version = MyDataVersionNumber.versionNumber
        self.user_agent_install_location = ""

        if hasattr(sys, 'frozen'):
            self.user_agent_install_location = os.path.dirname(sys.executable)
        else:
            try:
                self.user_agent_install_location = \
                    os.path.dirname(pkgutil.get_loader("MyDataVersionNumber")
                                    .filename)
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

        self.settingsModel.SetUploaderModel(self)

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

        url = myTardisUrl + "/api/v1/uploader/?format=json" + \
            "&mac_address=" + urllib.quote(self.mac_address)

        headers = {"Content-Type": "application/json",
                   "Accept": "application/json"}

        response = requests.get(headers=headers, url=url)
        existingMatchingUploaderRecords = response.json()
        numExistingMatchingUploaderRecords = \
            existingMatchingUploaderRecords['meta']['total_count']
        if numExistingMatchingUploaderRecords > 0:
            uploader_id = existingMatchingUploaderRecords['objects'][0]['id']

        logger.info("Uploading uploader info to MyTardis...")

        if numExistingMatchingUploaderRecords > 0:
            url = myTardisUrl + "/api/v1/uploader/%d/" % (uploader_id)
        else:
            url = myTardisUrl + "/api/v1/uploader/"

        uploaderJson = {"name": self.name,
                        "contact_name": self.contact_name,
                        "contact_email": self.contact_email,

                        "user_agent_name": self.user_agent_name,
                        "user_agent_version": self.user_agent_version,
                        "user_agent_install_location":
                            self.user_agent_install_location,

                        "os_platform": sys.platform,
                        "os_system": platform.system(),
                        "os_release": platform.release(),
                        "os_version": platform.version(),
                        "os_username": getpass.getuser(),

                        "machine": platform.machine(),
                        "architecture": str(platform.architecture()),
                        "processor": platform.processor(),
                        "memory": self._bytes2human(psutil.virtual_memory()
                                                    .total),
                        "cpus": psutil.cpu_count(),

                        "disk_usage": self.disk_usage,
                        "data_path": self.data_path,
                        "default_user": self.default_user,

                        "interface": self.interface,
                        "mac_address": self.mac_address,
                        "ipv4_address": self.ipv4_address,
                        "ipv6_address": self.ipv6_address,
                        "subnet_mask": self.subnet_mask,

                        "hostname": platform.node()}

        data = json.dumps(uploaderJson)
        if numExistingMatchingUploaderRecords > 0:
            response = requests.put(headers=headers, url=url, data=data)
        else:
            response = requests.post(headers=headers, url=url, data=data)
        if response.status_code >= 200 and response.status_code < 300:
            logger.info("Upload succeeded for uploader info.")
            self.json = response.json()
        else:
            logger.info("Upload failed for uploader info.")
            logger.info("Status code = " + str(response.status_code))
            logger.info(response.text)

    def ExistingUploadToStagingRequest(self):
        # FIXME: For now, the private key file path has to be ~/.ssh/MyData
        if not os.path.exists(os.path.join(os.path.expanduser("~"), ".ssh",
                                           "MyData")):
            message = "~/.ssh/MyData was not found, so we will " \
                      "generate a new key-pair and a new request " \
                      "for staging access."
            logger.info(message)
            raise PrivateKeyDoesNotExist(message)
        keyPair = OpenSSH.FindKeyPair("MyData")
        self.settingsModel.SetSshKeyPair(keyPair)
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        url = myTardisUrl + \
            "/api/v1/uploaderregistrationrequest/?format=json" + \
            "&uploader__mac_address=" + self.mac_address + \
            "&requester_key_fingerprint=" + \
            urllib.quote(keyPair.GetFingerprint())
        logger.debug(url)
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json"}
        response = requests.get(headers=headers, url=url)
        if response.status_code < 200 or response.status_code >= 300:
            if response.status_code == 404:
                raise DoesNotExist("HTTP 404 (Not Found) received for: " + url)
            raise Exception(response.text)
        existingMatchingUploaderRecords = response.json()
        numExistingMatchingUploaderRecords = \
            existingMatchingUploaderRecords['meta']['total_count']
        if numExistingMatchingUploaderRecords > 0:
            approval_json = existingMatchingUploaderRecords['objects'][0]
            logger.info("A request already exists for this uploader.")
            return approval_json
        else:
            message = "This uploader hasn't requested uploading " \
                      "via staging yet."
            logger.info(message)
            raise DoesNotExist(message)

    def RequestUploadToStagingApproval(self):
        """
        Used to request the ability to upload via "cat >>" over SSH
        to a staging area, and then register in MyTardis.
        """
        try:
            keyPair = OpenSSH.FindKeyPair("MyData")
        except PrivateKeyDoesNotExist:
            keyPair = OpenSSH.NewKeyPair("MyData")
        self.settingsModel.SetSshKeyPair(keyPair)
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        url = myTardisUrl + "/api/v1/uploaderregistrationrequest/"
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json"}
        uploaderRegistrationRequestJson = \
            {"uploader": self.json['resource_uri'],
             "name": self.name,
             "requester_name": self.contact_name,
             "requester_email": self.contact_email,
             "requester_public_key": keyPair.GetPublicKey(),
             "requester_key_fingerprint": keyPair.GetFingerprint()}
        data = json.dumps(uploaderRegistrationRequestJson)
        response = requests.post(headers=headers, url=url, data=data)
        if response.status_code >= 200 and response.status_code < 300:
            return response.json()
        else:
            if response.status_code == 404:
                raise DoesNotExist("HTTP 404 (Not Found) received for: " + url)
            logger.error("Status code = " + str(response.status_code))
            logger.error("URL = " + url)
            raise Exception(response.text)

    def RequestStagingAccess(self):
        try:
            self.UploadUploaderInfo()
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
            if uploadToStagingRequest['approved']:
                logger.info("Uploads to staging have been approved!")
            else:
                logger.info("Uploads to staging haven't been approved yet.")
            self.settingsModel\
                .SetUploadToStagingRequest(uploadToStagingRequest)
        except:
            logger.error(traceback.format_exc())

    def SetInstrument(self, instrument):
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        myTardisDefaultUsername = self.settingsModel.GetUsername()
        myTardisDefaultUserApiKey = self.settingsModel.GetApiKey()
        url = myTardisUrl + "/api/v1/uploader/?format=json" + \
            "&mac_address=" + urllib.quote(self.mac_address)
        logger.debug(url)
        headers = {"Authorization": "ApiKey " + myTardisDefaultUsername + ":" +
                   myTardisDefaultUserApiKey,
                   "Content-Type": "application/json",
                   "Accept": "application/json"}
        response = requests.get(headers=headers, url=url)
        existingMatchingUploaderRecords = response.json()
        numExistingMatchingUploaderRecords = \
            existingMatchingUploaderRecords['meta']['total_count']
        if numExistingMatchingUploaderRecords > 0:
            uploader_id = existingMatchingUploaderRecords['objects'][0]['id']
        else:
            raise DoesNotExist("SetInstrument: Uploader record not found!")
        logger.info("Setting instrument in uploader record via "
                    "MyTardis API...")
        url = myTardisUrl + "/api/v1/uploader/%d/" % (uploader_id)
        logger.debug(url)
        uploaderJson = {"instruments": [instrument.GetResourceUri()],
                        "mac_address": self.mac_address}
        data = json.dumps(uploaderJson)
        response = requests.put(headers=headers, url=url, data=data)
        if response.status_code >= 200 and response.status_code < 300:
            logger.info("Setting uploader's instrument succeeded.")
        else:
            logger.info("Setting uploader's instrument failed.")
            logger.info("Status code = " + str(response.status_code))
            logger.info(response.text)

    def GetActiveNetworkInterfaces(self):
        logger.info("Determining the active network interface...")
        activeInterfaces = []
        if sys.platform.startswith("win"):
            proc = subprocess.Popen(["netsh", "interface", "show", "interface"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = proc.communicate()
            if stderr is not None and stderr != "":
                logger.error(stderr)
            for row in stdout.split("\n"):
                m = re.match(r"^(Enabled|Disabled)\s*(Connected|Disconnected)\s*"
                             "(Dedicated|Internal|Loopback)\s*(.*)\s*$", row)
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
                    if adminState == "Enabled" and interfaceType == "Dedicated":
                        activeInterfaces.append(interface)
        elif sys.platform.startswith("darwin"):
            proc = subprocess.Popen(["route", "get", "default"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = proc.communicate()
            if stderr is not None and stderr != "":
                logger.error(stderr)
            for line in stdout.split("\n"):
                m = re.match(r"^\s*interface:\s+(\S+)\s*$", line)
                if m:
                    interface = m.groups()[0].strip()
                    activeInterfaces.append(interface)
        elif sys.platform.startswith("linux"):
            proc = subprocess.Popen(["route"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = proc.communicate()
            if stderr is not None and stderr != "":
                logger.error(stderr)
            for line in stdout.split("\n"):
                m = re.match(r"^default.*\s+(\S+)\s*$", line)
                if m:
                    interface = m.groups()[0].strip()
                    activeInterfaces.append(interface)

        return activeInterfaces

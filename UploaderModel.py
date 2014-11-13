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

import MyDataVersionNumber
from logger.Logger import logger
import OpenSSH


class UploaderModel():
    def __init__(self, settingsModel):
        self.settingsModel = settingsModel
        self.interface = None
        self.uploaderJson = None

        logger.info("Determining the active network interface...")
        proc = subprocess.Popen(["netsh", "interface", "show", "interface"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = proc.communicate()
        if stderr is not None and stderr != "":
            logger.error(stderr)
        activeInterfaces = []
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

        # Sometimes on Windows XP, you can end up with multiple results from
        # "netsh interface show interface"
        # If there is one called "Local Area Connection",
        # then that's the one we'll go with.
        if "Local Area Connection" in activeInterfaces:
            activeInterfaces = ["Local Area Connection"]
        elif "Local Area Connection 2" in activeInterfaces:
            activeInterfaces = ["Local Area Connection 2"]

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
                self.bytes2human(usage.total),
                self.bytes2human(usage.used),
                self.bytes2human(usage.free),
                int(usage.percent),
                part.fstype,
                part.mountpoint))

        self.disk_usage = disk_usage.strip()
        self.data_path = self.settingsModel.GetDataDirectory()
        self.default_user = self.settingsModel.GetUsername()

    def bytes2human(self, n):
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i + 1) * 10
        for s in reversed(symbols):
            if n >= prefix[s]:
                value = float(n) / prefix[s]
                return '%.1f%s' % (value, s)
        return "%sB" % n

    def uploadUploaderInfo(self):
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
                        "memory": self.bytes2human(psutil.virtual_memory()
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
            self.uploaderJson = response.json()
        else:
            logger.info("Upload failed for uploader info.")
            logger.info("Status code = " + str(response.status_code))
            logger.info(response.text)

    def existingUploadToStagingRequest(self):
        myTardisUrl = self.settingsModel.GetMyTardisUrl()
        url = myTardisUrl + "/api/v1/uploaderregistrationrequest/?format=json" + \
            "&uploader__mac_address=" + self.mac_address
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json"}
        response = requests.get(headers=headers, url=url)
        if response.status_code < 200 or response.status_code >= 300:
            if response.status_code == 404:
                raise Exception("HTTP 404 (Not Found) received for: " + url)
            raise Exception(response.text)
        existingMatchingUploaderRecords = response.json()
        numExistingMatchingUploaderRecords = \
            existingMatchingUploaderRecords['meta']['total_count']
        if numExistingMatchingUploaderRecords > 0:
            approval_json = existingMatchingUploaderRecords['objects'][0]
            logger.info("A request already exists for this uploader.")
            return approval_json
        else:
            logger.info("This uploader hasn't requested uploading "
                        "via staging yet.")
            return None

    def requestUploadToStagingApproval(self):
        """
        Used to request the ability to upload via RSYNC over SSH
        to a staging area, and then register in MyTardis.
        """

        keyPair = OpenSSH.findKeyPair("MyData")
        if keyPair is None:
            keyPair = OpenSSH.newKeyPair("MyData")

        myTardisUrl = self.settingsModel.GetMyTardisUrl()

        url = myTardisUrl + "/api/v1/uploaderregistrationrequest/"

        headers = {"Content-Type": "application/json",
                   "Accept": "application/json"}

        uploaderRegistrationRequestJson = \
            {"uploader": self.uploaderJson['resource_uri'],
             "name": self.name,
             "requester_name": self.contact_name,
             "requester_email": self.contact_email,
             "requester_public_key": keyPair.publicKey()}

        data = json.dumps(uploaderRegistrationRequestJson)
        response = requests.post(headers=headers, url=url, data=data)
        if response.status_code >= 200 and response.status_code < 300:
            return response.json()
        else:
            if response.status_code == 404:
                raise Exception("HTTP 404 (Not Found) received for: " + url)
            logger.error("Status code = " + str(response.status_code))
            logger.error("URL = " + url)
            raise Exception(response.text)

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

import MyDataVersionNumber
from logger.Logger import logger


class UploaderModel():
    def __init__(self, settingsModel):
        self.settingsModel = settingsModel

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

    def upload_uploader_info(self):

        logger.info("Determining the active network interface...")

        proc = subprocess.Popen(["netsh", "interface", "show", "interface"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = proc.communicate()
        if stderr is not None and stderr != "":
            logger.error(stderr)
        activeInterfaces = []
        for row in stdout.split("\n"):
            m = re.match(r"^(Enabled|Disabled)\s*(Connected|Disconnected)\s*(Dedicated|Internal|Loopback)\s*(.*)\s*$", row)
            if m:
                adminState = m.groups()[0]
                state = m.groups()[1]
                interfaceType = m.groups()[2]
                interface = m.groups()[3].strip()
                if adminState == "Enabled" and state == "Connected" and interfaceType == "Dedicated":
                    activeInterfaces.append(interface)
            # On Windows XP, the state may be blank:
            m = re.match(r"^(Enabled|Disabled)\s*(Dedicated|Internal|Loopback)\s*(.*)\s*$", row)
            if m:
                adminState = m.groups()[0]
                interfaceType = m.groups()[1]
                interface = m.groups()[2].strip()
                if adminState == "Enabled" and interfaceType == "Dedicated":
                    activeInterfaces.append(interface)

        # Sometimes on Windows XP, you can end up with multiple results from "netsh interface show interface"
        # If there is one called "Local Area Connection", that's the one we'll go with.
        if "Local Area Connection" in activeInterfaces:
            activeInterfaces = ["Local Area Connection"]
        elif "Local Area Connection 2" in activeInterfaces:
            activeInterfaces = ["Local Area Connection 2"]

        proc = subprocess.Popen(["ipconfig", "/all"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
                        ipv4_address[interface] = value.strip().replace("(Preferred)", "")
                    if "IPv6 Address" in key.strip(' .'):
                        ipv6_address[interface] = value.strip().replace("(Preferred)", "")
                    if "Subnet Mask" in key.strip(' .'):
                        subnet_mask[interface] = value.strip()

        interface = activeInterfaces[0]

        logger.info("The active network interface is: " + str(interface))

        myTardisUrl = self.settingsModel.GetMyTardisUrl()

        url = myTardisUrl + "/api/v1/uploader/?format=json" + \
            "&mac_address=" + mac_address[interface]

        headers = \
            {
               "Content-Type": "application/json",
               "Accept": "application/json"
            }

        response = requests.get(headers=headers, url=url)
        existingMatchingUploaderRecords = response.json()
        numExistingMatchingUploaderRecords = \
            existingMatchingUploaderRecords['meta']['total_count']
        if numExistingMatchingUploaderRecords > 0:
            uploader_id = existingMatchingUploaderRecords['objects'][0]['id']

        name = self.settingsModel.GetInstrumentName()
        contact_name = self.settingsModel.GetContactName()
        contact_email = self.settingsModel.GetContactEmail()

        user_agent_name = "MyData"
        user_agent_version = MyDataVersionNumber.versionNumber
        user_agent_install_location = ""

        if hasattr(sys, 'frozen'):
            user_agent_install_location = os.path.dirname(sys.executable)
        else:
            try:
                user_agent_install_location = os.path.dirname(pkgutil.get_loader("MyDataVersionNumber").filename)
            except:
                user_agent_install_location = os.getcwd()

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

        data_path = self.settingsModel.GetDataDirectory()
        default_user = self.settingsModel.GetUsername()

        logger.info("Uploading uploader info to MyTardis...")

        uploaderJson = \
                {
                        "interface": interface, 
                        "mac_address": mac_address[interface], 

                        "name": name, 
                        "contact_name": contact_name, 
                        "contact_email": contact_email,

                        "user_agent_name": user_agent_name,
                        "user_agent_version": user_agent_version,
                        "user_agent_install_location": user_agent_install_location,

                        "os_platform": sys.platform,
                        "os_system": platform.system(),
                        "os_release": platform.release(),
                        "os_version": platform.version(),
                        "os_username": getpass.getuser(),

                        "machine": platform.machine(),
                        "architecture": str(platform.architecture()),
                        "processor": platform.processor(),
                        "memory": self.bytes2human(psutil.virtual_memory().total),
                        "cpus": psutil.cpu_count(),

                        "disk_usage": disk_usage.strip(),
                        "data_path": data_path,
                        "default_user": default_user,

                        "interface": interface,
                        "ipv4_address": ipv4_address[interface],
                        "ipv6_address": ipv6_address[interface],
                        "subnet_mask": subnet_mask[interface],

                        "hostname": platform.node()
                }

        if numExistingMatchingUploaderRecords > 0:
            url = myTardisUrl + "/api/v1/uploader/%d/" % (uploader_id)
        else:
            url = myTardisUrl + "/api/v1/uploader/"

        headers = \
            {
               "Content-Type": "application/json",
               "Accept": "application/json"
            }
        data = json.dumps(uploaderJson)
        if numExistingMatchingUploaderRecords > 0:
            response = requests.put(headers=headers, url=url, data=data)
        else:
            response = requests.post(headers=headers, url=url, data=data)
        if response.status_code>=200 and response.status_code<300:
            logger.info("Upload succeeded for uploader info.")
        else:
            logger.info("Upload failed for uploader info.")
            logger.info("Status code = " + str(response.status_code))
            logger.info(response.text)


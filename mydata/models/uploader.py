"""
mydata/models/uploader.py

The purpose of this module is to help with registering MyData uploaders
(which are usually instrument PCs) with the MyTardis server.

MyData POSTs some basic information about the PC and about the MyData
installation to its MyTardis server.  This basic information is called an
"Uploader" record.  The Uploader is made unique by a locally-generated
UUID, so each MyData instance should only have one Uploader record in MyTardis.

Initially only HTTP POST uploads are enabled in MyData, but MyData will
request uploads via SFTP to a staging area, and wait for a MyTardis
administrator to approve the request (which requires updating the
UploaderRegistrationRequest record created by MyData in the Djano Admin
interface).

The IP address information provided in the Uploader record can be used
on the SFTP server to grant access via /etc/hosts.allow or equivalent.

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
import traceback
import uuid

from six.moves import urllib

import dateutil.parser
import psutil
import requests
import netifaces

from .. import __version__ as VERSION
from ..logs import logger
from ..utils.connectivity import GetDefaultInterfaceType
from ..utils.exceptions import DoesNotExist
from ..utils.exceptions import PrivateKeyDoesNotExist
from ..utils.exceptions import MissingMyDataAppOnMyTardisServer
from ..utils.exceptions import StorageBoxOptionNotFound
from ..utils.exceptions import StorageBoxAttributeNotFound
from ..utils import BytesToHuman
from ..utils import MyDataInstallLocation
from ..threads.locks import LOCKS
from .storage import StorageBox


class UploaderModel(object):
    """
    Model class for MyTardis API v1's UploaderAppResource.
    """
    def __init__(self, settings):
        # pylint: disable=too-many-branches
        self.settings = settings
        self.uploaderId = None
        self.resourceUri = None
        self.uploaderSettings = None
        self.uploadToStagingRequest = None
        self.settingsUpdated = None
        self.sshKeyPair = None

        self.sysInfo = dict(
            osPlatform=sys.platform,
            osSystem=platform.system(),
            osRelease=platform.release(),
            osVersion=platform.version(),
            osUsername=getpass.getuser(),
            machine=platform.machine(),
            architecture=str(platform.architecture()),
            processor=platform.processor(),
            memory=BytesToHuman(psutil.virtual_memory().total),
            cpus=psutil.cpu_count(),
            hostname=platform.node())

        self.ifconfig = dict(interface=None, macAddress='', ipv4Address='',
                             ipv6Address='', subnetMask='')

        if self.settings.miscellaneous.uuid is None:
            self.settings.miscellaneous.uuid = str(uuid.uuid1())

        defaultInterfaceType = GetDefaultInterfaceType()
        if defaultInterfaceType:
            self.ifconfig['interface'] = \
                netifaces.gateways()['default'][defaultInterfaceType][1]
            ifaddresses = netifaces.ifaddresses(self.ifconfig['interface'])
            if netifaces.AF_LINK in ifaddresses.keys():
                self.ifconfig['macAddress'] = \
                    ifaddresses[netifaces.AF_LINK][0]['addr']
            if netifaces.AF_INET in ifaddresses:
                ipv4Addrs = ifaddresses[netifaces.AF_INET]
                self.ifconfig['ipv4Address'] = ipv4Addrs[0]['addr']
                self.ifconfig['subnetMask'] = ipv4Addrs[0]['netmask']
            if netifaces.AF_INET6 in ifaddresses:
                ipv6Addrs = ifaddresses[netifaces.AF_INET6]
                if sys.platform.startswith("win"):
                    self.ifconfig['ipv6Address'] = ipv6Addrs[0]['addr']
                else:
                    for addr in ipv6Addrs:
                        match = re.match(r'(.+)%(.+)', addr['addr'])
                        if match and \
                                match.group(2) == self.ifconfig['interface']:
                            self.ifconfig['ipv6Address'] = match.group(1)
            logger.debug("The active network interface is: %s"
                         % str(self.ifconfig['interface']))
        else:
            logger.warning("There is no active network interface.")

    def UploadUploaderInfo(self):
        """
        Uploads info about the instrument PC to MyTardis via HTTP POST

        :raises requests.exceptions.HTTPError:
        """
        # pylint: disable=too-many-branches
        myTardisUrl = self.settings.general.myTardisUrl
        url = myTardisUrl + "/api/v1/mydata_uploader/?format=json" + \
            "&uuid=" + urllib.parse.quote(self.settings.miscellaneous.uuid)
        headers = self.settings.defaultHeaders
        response = requests.get(
            headers=headers, url=url,
            timeout=self.settings.miscellaneous.connectionTimeout)
        response.raise_for_status()
        existingUploaderRecords = response.json()
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

        uploaderJson = {
            "uuid": self.settings.miscellaneous.uuid,
            "name": self.settings.general.instrumentName,
            "contact_name": self.settings.general.contactName,
            "contact_email": self.settings.general.contactEmail,

            "user_agent_name": "MyData",
            "user_agent_version": VERSION,
            "user_agent_install_location": MyDataInstallLocation(),

            "os_platform": self.sysInfo['osPlatform'],
            "os_system": self.sysInfo['osSystem'],
            "os_release": self.sysInfo['osRelease'],
            "os_version": self.sysInfo['osVersion'],
            "os_username": self.sysInfo['osUsername'],

            "machine": self.sysInfo['machine'],
            "architecture": self.sysInfo['architecture'],
            "processor": self.sysInfo['processor'],
            "memory": self.sysInfo['memory'],
            "cpus": self.sysInfo['cpus'],

            "disk_usage": "",
            "data_path": self.settings.general.dataDirectory,
            "default_user": self.settings.general.username,

            "interface": self.ifconfig['interface'],
            "mac_address": self.ifconfig['macAddress'],
            "ipv4_address": self.ifconfig['ipv4Address'],
            "ipv6_address": self.ifconfig['ipv6Address'],
            "subnet_mask": self.ifconfig['subnetMask'],

            "hostname": self.sysInfo['hostname'],

            "instruments": [self.settings.general.instrument.resourceUri]
        }

        data = json.dumps(uploaderJson, indent=4)
        logger.debug(data)
        headers = self.settings.defaultHeaders
        if numExistingUploaderRecords > 0:
            response = requests.put(
                headers=headers, url=url, data=data.encode(),
                timeout=self.settings.miscellaneous.connectionTimeout)
        else:
            response = requests.post(
                headers=headers, url=url, data=data.encode(),
                timeout=self.settings.miscellaneous.connectionTimeout)
        response.raise_for_status()
        logger.debug("Upload succeeded for uploader info.")
        self.resourceUri = response.json()['resource_uri']

    @property
    def name(self):
        """
        For now the uploader name is the same as the instrument name, but
        that could change if we ever support uploading data from multiple
        instruments using the same MyData instance.
        """
        return self.settings.general.instrumentName

    @property
    def userAgentInstallLocation(self):
        """
        Return MyData install location
        """
        if hasattr(sys, 'frozen'):
            return os.path.dirname(sys.executable)
        try:
            return os.path.realpath(
                os.path.join(os.path.dirname(__file__), "..", ".."))
        except:
            return os.getcwd()

    @property
    def hostname(self):
        """
        Return the instrument PC's hostname
        """
        return self.sysInfo['hostname']

    def ExistingUploadToStagingRequest(self):
        """
        Look for existing upload to staging request.

        Ensures that a MyData SSH key-pair exists, creating one if needed.

        :raises requests.exceptions.HTTPError:
        """
        from mydata.utils.openssh import FindOrCreateKeyPair

        if not self.sshKeyPair:
            self.sshKeyPair = FindOrCreateKeyPair()
        myTardisUrl = self.settings.general.myTardisUrl
        url = myTardisUrl + \
            "/api/v1/mydata_uploaderregistrationrequest/?format=json" + \
            "&uploader__uuid=" + self.settings.miscellaneous.uuid + \
            "&requester_key_fingerprint=" + urllib.parse.quote(
                self.sshKeyPair.fingerprint)
        logger.debug(url)
        headers = self.settings.defaultHeaders
        response = requests.get(headers=headers, url=url)
        response.raise_for_status()
        logger.debug(response.text)
        existingUploaderRegReqRecords = response.json()
        if existingUploaderRegReqRecords['meta']['total_count'] > 0:
            approvalJson = existingUploaderRegReqRecords['objects'][0]
            logger.debug("A request already exists for this uploader.")
            return UploaderRegistrationRequest(
                uploaderRegRequestJson=approvalJson)
        message = "This uploader hasn't requested uploading " \
                  "via staging yet."
        logger.debug(message)
        raise DoesNotExist(message)

    def RequestUploadToStagingApproval(self):
        """
        Used to request the ability to upload via SFTP
        to a staging area, and then register in MyTardis.

        :raises requests.exceptions.HTTPError:
        """
        from mydata.utils.openssh import FindOrCreateKeyPair

        if not self.sshKeyPair:
            self.sshKeyPair = FindOrCreateKeyPair()
        myTardisUrl = self.settings.general.myTardisUrl
        url = myTardisUrl + "/api/v1/mydata_uploaderregistrationrequest/"
        uploaderRegistrationRequestJson = \
            {"uploader": self.resourceUri,
             "name": self.settings.general.instrumentName,
             "requester_name": self.settings.general.contactName,
             "requester_email": self.settings.general.contactEmail,
             "requester_public_key": self.sshKeyPair.publicKey,
             "requester_key_fingerprint": self.sshKeyPair.fingerprint}
        data = json.dumps(uploaderRegistrationRequestJson)
        response = requests.post(headers=self.settings.defaultHeaders, url=url,
                                 data=data.encode())
        response.raise_for_status()
        return UploaderRegistrationRequest(
            uploaderRegRequestJson=response.json())

    def RequestStagingAccess(self):
        """
        This could be called from multiple threads simultaneously,
        so it requires locking.
        """
        with LOCKS.requestStagingAccess:
            try:
                try:
                    self.UploadUploaderInfo()
                except:
                    logger.error(traceback.format_exc())
                    raise
                try:
                    self.uploadToStagingRequest = \
                        self.ExistingUploadToStagingRequest()
                except DoesNotExist:
                    self.uploadToStagingRequest = \
                        self.RequestUploadToStagingApproval()
                    logger.debug("Uploader registration request created.")
                except PrivateKeyDoesNotExist:
                    logger.debug(
                        "Generating new uploader registration request, "
                        "because private key was moved or deleted.")
                    self.uploadToStagingRequest = \
                        self.RequestUploadToStagingApproval()
                    logger.debug("Generated new uploader registration request,"
                                 " because private key was moved or deleted.")
                if self.uploadToStagingRequest.approved:
                    logger.debug("Uploads to staging have been approved!")
                else:
                    logger.debug(
                        "Uploads to staging haven't been approved yet.")
            except:
                logger.error(traceback.format_exc())
                raise

    def UpdateSettings(self, settingsList):
        """
        Used to save uploader settings to the mytardis-app-mydata's
        UploaderSettings model on the MyTardis server.

        :raises requests.exceptions.HTTPError:
        """
        myTardisUrl = self.settings.general.myTardisUrl
        headers = self.settings.defaultHeaders

        if not self.uploaderId:
            url = "%s/api/v1/mydata_uploader/?format=json&uuid=%s" \
                % (myTardisUrl,
                   urllib.parse.quote(self.settings.miscellaneous.uuid))
            response = requests.get(headers=headers, url=url)
            response.raise_for_status()
            existingUploaderRecords = response.json()
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
            'uuid': self.settings.miscellaneous.uuid
        }
        response = requests.patch(headers=headers, url=url,
                                  data=json.dumps(patchData).encode())
        response.raise_for_status()

    def GetSettings(self):
        """
        Used to retrieve uploader settings from the mytardis-app-mydata's
        UploaderSettings model on the MyTardis server.

        :raises requests.exceptions.HTTPError:
        """
        myTardisUrl = self.settings.general.myTardisUrl
        headers = self.settings.defaultHeaders
        url = "%s/api/v1/mydata_uploader/?format=json&uuid=%s" \
            % (myTardisUrl, urllib.parse.quote(self.settings.miscellaneous.uuid))
        try:
            response = requests.get(
                headers=headers, url=url,
                timeout=self.settings.miscellaneous.connectionTimeout)
        except Exception as err:
            logger.error(str(err))
            raise
        if response.status_code == 404:
            message = "The MyData app is missing from the MyTardis server."
            logger.error(url)
            logger.error(message)
            raise MissingMyDataAppOnMyTardisServer(message)
        response.raise_for_status()
        existingUploaderRecords = response.json()
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
                logger.debug("settings_updated: %s" % settingsUpdatedString)
                if settingsUpdatedString:
                    self.settingsUpdated = \
                        dateutil.parser.parse(settingsUpdatedString)
            else:
                self.uploaderSettings = None

        return self.uploaderSettings


class UploaderRegistrationRequest(object):
    """
    Model class for MyTardis API v1's UploaderRegistrationRequestAppResource.
    See: https://github.com/mytardis/mytardis-app-mydata/blob/master/api.py

    The upload-to-staging request contains information indicating whether the
    request has been approved i.e. the MyData.pub public key has been installed
    on the SFTP server, and the approved storage box (giving the remote file
    path to upload to, and the SFTP username, hostname and port).
    """
    def __init__(self, uploaderRegRequestJson=None):
        self.uploaderRegRequestJson = uploaderRegRequestJson

    @property
    def approved(self):
        """
        Return True if uploader registration request has been approved
        """
        return self.uploaderRegRequestJson['approved']

    @property
    def approvedStorageBox(self):
        """
        Return approved storage box
        """
        storageBoxJson = self.uploaderRegRequestJson['approved_storage_box']
        return StorageBox(storageBoxJson=storageBoxJson)

    @property
    def scpUsername(self):
        """
        Return 'scp_username' storage box attribute
        """
        for attribute in self.approvedStorageBox.attributes:
            if attribute.key == "scp_username":
                return attribute.value
        raise StorageBoxAttributeNotFound(
            self.approvedStorageBox, "scp_username")

    @property
    def scpHostname(self):
        """
        Return 'scp_hostname' storage box attribute
        """
        for attribute in self.approvedStorageBox.attributes:
            if attribute.key == "scp_hostname":
                return attribute.value
        raise StorageBoxAttributeNotFound(
            self.approvedStorageBox, "scp_hostname")

    @property
    def scpPort(self):
        """
        Return 'scp_port' storage box attribute
        """
        for attribute in self.approvedStorageBox.attributes:
            if attribute.key == "scp_port":
                return attribute.value
        return "22"

    @property
    def location(self):
        """
        Return 'location' storage box option
        """
        for option in self.approvedStorageBox.options:
            if option.key == "location":
                return option.value
        raise StorageBoxOptionNotFound(self.approvedStorageBox, "location")

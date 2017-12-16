"""
Model class for the settings not displayed in the settings dialog,
but accessible in MyData.cfg, or in the case of "locked", visible in the
settings dialog, but not specific to any one tab view.

Also includes miscellaneous functionality which needed to be moved out of
the main settings model module (model.py) to prevent cyclic imports.
"""
import sys

from .base import BaseSettingsModel


class LastSettingsUpdateTrigger(object):
    """
    Enumerated data type encapsulating the trigger for the last change to
    the settings.

    This is used to determine whether settings validation is required.

    If the user opens the settings dialog, and clicks OK, validation is
    performed automatically, so there is no need to validate settings
    again at the beginning of a scan-folders-and-upload task commenced
    shortly after closing the settings dialog.

    However, if MyData finds a MyData.cfg on disk when it launches, and
    then the user clicks the "Upload" button without opening the settings
    dialog first, then we do need to validate settings.
    """
    # The last update to SETTINGS came from reading MyData.cfg from disk:
    READ_FROM_DISK = 0
    # The last update to SETTINGS came from the settings dialog:
    UI_RESPONSE = 1


class MiscellaneousSettingsModel(BaseSettingsModel):
    """
    Model class for the settings not displayed in the settings dialog,
    but accessible in MyData.cfg, or in the case of "locked", visible in the
    settings dialog, but not specific to any one tab view.
    """
    def __init__(self):
        # Saved in MyData.cfg:
        self.mydataConfig = dict()

        self.fields = [
            'locked',
            'uuid',
            'verification_delay',
            'max_verification_threads',
            'fake_md5_sum',
            'cipher',
            'use_none_cipher',
            'progress_poll_interval',
            'immutable_datasets',
            'cache_datafile_lookups'
        ]

        self.default = dict(
            locked=False,
            uuid=None,
            verification_delay=3.0,
            max_verification_threads=5,
            fake_md5_sum=False,
            cipher="aes128-ctr",
            use_none_cipher=False,
            progress_poll_interval=1.0,
            immutable_datasets=False,
            cache_datafile_lookups=True)

    @property
    def locked(self):
        """
        Settings Dialog's Lock/Unlock button

        Return True if settings are locked
        """
        return self.mydataConfig['locked']

    @locked.setter
    def locked(self, locked):
        """
        Settings Dialog's Lock/Unlock button

        Set this to True to lock settings
        """
        self.mydataConfig['locked'] = locked

    @property
    def uuid(self):
        """
        Get this MyData instance's unique ID
        """
        return self.mydataConfig['uuid']

    @uuid.setter
    def uuid(self, uuid):
        """
        Set this MyData instance's unique ID
        """
        self.mydataConfig['uuid'] = uuid

    @property
    def fakeMd5Sum(self):
        """
        Whether to use a fake MD5 sum to save time.
        It can be set later via the MyTardis API.
        Until it is set properly, the file won't be
        verified on MyTardis.
        """
        return self.mydataConfig['fake_md5_sum']

    @property
    def verificationDelay(self):
        """
        Upon a successful upload, MyData will request verification
        after a short delay, defaulting to 3 seconds:

        :return: the delay in seconds
        :rtype: float
        """
        return self.mydataConfig['verification_delay']

    @property
    def maxVerificationThreads(self):
        """
        Return the maximum number of concurrent DataFile lookups
        """
        return int(self.mydataConfig['max_verification_threads'])

    @maxVerificationThreads.setter
    def maxVerificationThreads(self, maxVerificationThreads):
        """
        Set the maximum number of concurrent DataFile lookups
        """
        self.mydataConfig['max_verification_threads'] = maxVerificationThreads

    @staticmethod
    def GetFakeMd5Sum():
        """
        The fake MD5 sum to use when self.FakeMd5Sum()
        is True.
        """
        return "00000000000000000000000000000000"

    @property
    def cipher(self):
        """
        SSH Cipher for SCP uploads.
        """
        return self.mydataConfig['cipher']

    @property
    def useNoneCipher(self):
        """
        If True, self.mydataConfig['cipher'] is ignored.
        """
        return self.mydataConfig['use_none_cipher']

    @useNoneCipher.setter
    def useNoneCipher(self, useNoneCipher):
        """
        If True, self.mydataConfig['cipher is ignored.
        """
        self.mydataConfig['use_none_cipher'] = useNoneCipher

    @property
    def cipherOptions(self):
        """
        SSH Cipher Options for SCP uploads.
        """
        if self.mydataConfig['use_none_cipher']:
            return ["-oNoneEnabled=yes", "-oNoneSwitch=yes"]
        return ["-c", self.mydataConfig['cipher']]

    @property
    def progressPollInterval(self):
        """
        Upload progress is queried periodically via the MyTardis API.
        Returns the interval in seconds between RESTful progress queries.

        :return: the interval in seconds
        :rtype: float
        """
        return self.mydataConfig['progress_poll_interval']

    @property
    def immutableDatasets(self):
        """
        Returns True if MyData will set immutable to True
        for newly created datasets
        """
        return self.mydataConfig['immutable_datasets']

    @immutableDatasets.setter
    def immutableDatasets(self, immutableDatasets):
        """
        If True, MyData will set immutable to True
        for newly created datasets
        """
        self.mydataConfig['immutable_datasets'] = immutableDatasets

    @property
    def cacheDataFileLookups(self):
        """
        Returns True if MyData will cache local paths and dataset IDs of
        datafiles which have been previously found to be verified on MyTardis.
        """
        return self.mydataConfig['cache_datafile_lookups']

    @cacheDataFileLookups.setter
    def cacheDataFileLookups(self, cacheDataFileLookups):
        """
        Set this to True if MyData should cache local paths and dataset IDs of
        datafiles which have been previously found to be verified on MyTardis.
        """
        self.mydataConfig['cache_datafile_lookups'] = cacheDataFileLookups

    def SetDefaultForField(self, field):
        """
        Set default value for one field.
        """
        self.mydataConfig[field] = self.default[field]
        if field == 'cipher':
            if sys.platform.startswith("win"):
                self.mydataConfig['cipher'] = \
                    "aes128-gcm@openssh.com,aes128-ctr"
            else:
                # On Mac/Linux, we don't bundle SSH binaries, we
                # just use the installed SSH version, which might
                # be too old to support aes128-gcm@openssh.com
                self.mydataConfig['cipher'] = "aes128-ctr"

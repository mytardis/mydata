"""
Model class for the settings not displayed in the settings dialog,
but accessible in MyData.cfg, or in the case of "locked", visible in the
settings dialog, but not specific to any one tab view.

Also includes miscellaneous functionality which needed to be moved out of
the main settings model module (model.py) to prevent cyclic imports.
"""
import sys


class LastSettingsUpdateTrigger(object):
    """
    Enumerated data type encapsulating the trigger
    for the settings update, either:
        LastSettingsUpdateTrigger.READ_FROM_DISK or
        LastSettingsUpdateTrigger.UI_RESPONSE
    """
    READ_FROM_DISK = 0
    UI_RESPONSE = 1


class MiscellaneousSettingsModel(object):
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
            'progress_poll_interval'
        ]

    @property
    def locked(self):
        """
        Return True if settings are locked
        """
        return self.mydataConfig['locked']

    @locked.setter
    def locked(self, locked):
        """
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
        """
        return float(self.mydataConfig['verification_delay'])

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
        If True, self.mydataConfig['cipher is ignored.
        """
        return self.mydataConfig['use_none_cipher']

    @useNoneCipher.setter
    def useNoneCipher(self, useNoneCipher):
        """
        If True, self.mydataConfig['cipher is ignored.
        """
        self.mydataConfig['use_none_cipher'] = useNoneCipher

    @property
    def progressPollInterval(self):
        """
        Stored as an int in MyData.cfg, but used
        as a float in threading.Timer(...)
        """
        return float(self.mydataConfig['progress_poll_interval'])

    def SetDefaults(self):
        """
        Set default values for configuration parameters that will appear in
        MyData.cfg for miscellaneous fields not in the Settings Dialog.
        """
        # Settings Dialog's Lock/Unlock button:
        self.mydataConfig['locked'] = False

        # MyData instance's unique ID:
        self.mydataConfig['uuid'] = None

        # Upon a successful upload, MyData will request verification
        # after a short delay, defaulting to 3 seconds:
        self.mydataConfig['verification_delay'] = 3

        self.mydataConfig['max_verification_threads'] = 5

        # If True, don't calculate an MD5 sum, just provide a string of zeroes:
        self.mydataConfig['fake_md5_sum'] = False

        if sys.platform.startswith("win"):
            self.mydataConfig['cipher'] = "aes128-gcm@openssh.com,aes128-ctr"
        else:
            # On Mac/Linux, we don't bundle SSH binaries, we
            # just use the installed SSH version, which might
            # be too old to support aes128-gcm@openssh.com
            self.mydataConfig['cipher'] = "aes128-ctr"
        self.mydataConfig['use_none_cipher'] = False

        # Interval in seconds between RESTful progress queries:
        self.mydataConfig['progress_poll_interval'] = 1

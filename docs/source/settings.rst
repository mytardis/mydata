
.. _mydata-settings-dialog:

Settings
========

MyData's Settings dialog can be opened by clicking on the |settings| icon on
MyData's toolbar, or by selecting the "MyData Settings" menu item in the 
MyData System Tray icon's pop-up menu.  The Settings dialog will be
automatically displayed the first time MyData is launched.

.. |settings| image:: images/Settings.png


General
^^^^^^^

  .. image:: images/SettingsGeneral.PNG

**Instrument Name**
  The name of the instrument (e.g. "Nikon Microscope #1") whose data
  is to be uploaded to MyTardis by this MyData instance.  If an instrument
  record with this name doesn't already exist in MyTardis within the facility
  specified below, then MyData will offer to create one (assuming that you are
  a member of a facility managers group for that facility in MyTardis).

**Facility Name**
  The name of the facility containing the instrument to upload data from.  A
  facility record must have been created by your MyTardis administrator before
  you can use MyData, and the default MyTardis username you enter below (the
  initial owner of all data uploaded by this instance) must be a member of the
  managers group for that facility.  MyData will automatically check that a
  facility record matching this facility name exists on the MyTardis server
  specified by the MyTardis URL below.  If it doesn't exist, MyData will offer
  suggestions for alternative facilities which your MyTardis account is a 
  manager of (if any).

**Contact Name**
  MyData's preferred upload method (staging) requires approval from a MyTardis
  administrator. This Contact Name will be used when sending confirmation that
  access to MyTardis's staging area has been approved for this MyData instance.

**Contact Email**
  MyData's preferred upload method (staging) requires approval from a MyTardis
  administrator. This Contact Email will be used when sending confirmation that
  access to MyTardis's staging area has been approved for this MyData instance.

**Data Directory**
  Choose a folder where you would like to store your data. e.g. D:\\Data

**MyTardis URL**
  The URL of a MyTardis server running a MyTardis version compatible with
  MyData, e.g. http://118.138.241.91/

**MyTardis Username**
  Do not put your individual MyTardis username (e.g. "jsmith") in
  here.  Because MyData is designed to be able to upload multiple users' data
  from an instrument PC, the default username used by MyData should generally
  be a facility role account, e.g. "testfacility".

**MyTardis API Key**
  API keys are similar to passwords, but they are easier to revoke and renew
  when necessary. Ask your MyTardis administrator for the API key corresponding
  to your facility role account.

  .. image:: images/DownloadApiKey.png


.. _settings-dialog-schedule:

Schedule
^^^^^^^^

  .. image:: images/SettingsSchedule.PNG

**Schedule types**

  .. image:: images/ScheduleTypeComboBox.png

**Schedule type - On Startup**
    Run the folder scans and uploads automatically when MyData is launched.

**Schedule type - On Settings Saved**
    Run the folder scans and uploads automatically afte the user clicks OK
    on the Settings dialog.

**Schedule type - Manually**
    Only run the folder scans and uploads in response to user interaction -
    either by clicking the Refresh icon on the toolbar, or by clicking the
    "Sync Now" menu item in the system tray menu.

**Schedule type - Once**
    Run the folder scans and uploads once, on the date specified by the Date
    field and at the time specified by the Time field.

**Schedule type - Daily**
    Run the folder scans and uploads every day, at the time specified by the
    Time field.

**Schedule type - Weekly**
    Run the folder scans and uploads every week on the day(s) specified by the
    weekday checkboxes, at the time specified by the Time field.

**Schedule type - Timer**
    Run the folder scans and uploads repeatedly with an interval specified by
    the "Timer (minutes)" field between the hours of "From" and "To", every day.


.. _settings-dialog-filters:

Filters
^^^^^^^

  .. image:: images/SettingsFilters.PNG

**Username/Email/User Group folder name contains**
    Only scan user folders (or user group folders) whose username (or email
    or user group) contains the string provided.  The actual text of this
    setting will change, depending on the Folder Structure specified in the
    Advanced tab.

**Dataset folder name contains**
    Only scan dataset folders whose folder name contains the string provided.

**Experiment folder name contains**
    Only scan experiment folders whose folder name contains the string
    provided.  This field will be hidden unless the Folder Structure
    specified in the Advanced tab includes an Experiment folder.

**Ignore datasets older than**
  MyData is designed to be used for uploading recent data.  If it is configured
  to use an existing data directory containing a large backlog of old data, it
  is advisable to instruct MyData to ignore old datasets so that it focus on
  uploading the recent datasets.

**Ignore files newer than**
  MyData can ignore recently modified files.  MyTardis does not yet support
  file versioning, so once a file has been uploaded and verified, it will not
  be replaced by a newer version.  Therefore, it is important to ensure that
  a file doesn't get uploaded while it is still being modified.

**Includes files matching patterns in**
  Specifying an includes file will tell MyData to only upload files
  matching specified patterns, e.g. '\*.txt'. The includes file should
  contain one pattern on each line.  Any lines beginning with '#' or ';'
  will be ignored.  The patterns will be matched using Python's fnmatch:
  https://docs.python.org/2/library/fnmatch.html
  If both an includes and an excludes file are specified, then filenames
  matching one or more includes patterns will be uploaded, even if they
  also match one or more excludes patterns.

**Excludes files matching patterns in**
  Specifying an excludes file will tell MyData not to upload files
  matching specified patterns, e.g. \*.bak The excludes file should
  contain one pattern on each line.  Any lines beginning with '#' or ';'
  will be ignored.  The patterns will be matched using Python's fnmatch:
  https://docs.python.org/2/library/fnmatch.html
  If both an includes and an excludes file are specified, then filenames
  matching one or more includes patterns will be uploaded, even if they
  also match one or more excludes patterns.

.. _settings-dialog-advanced:

Advanced
^^^^^^^^

  .. image:: images/SettingsAdvanced.PNG

**Folder Structure - Username / Dataset**
    Folders immediately inside the main data directory
    (e.g. "D:\\Data\\jsmith") are assumed to be MyTardis usernames.
    Folders inside each user folder (e.g. "D:\\Data\\jsmith\\Dataset1"
    will be mapped to MyTardis datasets.
    Datasets will be automatically grouped into MyTardis experiments according
    to the "Experiment (Dataset Grouping)" field below.

**Folder Structure - Email / Dataset**
    This folder structure works best when email addresses are unique per
    user in MyTardis.  There is no constraint requiring email addresses to be
    unique in MyTardis, but if MyTardis is using an external authentication
    provider (e.g. LDAP), there may be a requirement in the authentication
    provider making email addresses unique.
    Folders immediately inside the main data directory
    (e.g. "D:\\Data\\John.Smith@example.com") are assumed to be email
    addresses which can be used to match MyTardis user accounts.  If you wish
    to use email addresses as folder names, an alternative is to use the
    "Username / Dataset" folder structure and use email addresses
    for usernames in MyTardis.  Folders inside each email folder (e.g.
    "D:\\Data\\John.Smith@example.com\\Dataset1" will be mapped to
    MyTardis datasets.  Datasets will be automatically grouped into MyTardis
    experiments according to the "Experiment (Dataset Grouping)"
    field below.

**Folder Structure - Username / Experiment / Dataset**
    Folders immediately inside the main data directory
    (e.g. "D:\\Data\\jsmith") are assumed to be MyTardis usernames.
    Folders inside each user folder (e.g. "D:\\Data\\jsmith\\Experiment1"
    will be mapped to MyTardis experiments.  Folders inside each experiment
    folder (e.g. "D:\\Data\\jsmith\\Experiment1\\Dataset1") will be
    mapped to MyTardis datasets.

**Folder Structure - Email / Experiment / Dataset**
    This folder structure works best when email addresses are unique per
    user in MyTardis.  There is no constraint requiring email addresses to be
    unique in MyTardis, but if MyTardis is using an external authentication
    provider (e.g. LDAP), there may be a requirement in the authentication
    provider making email addresses unique.
    Folders immediately inside the main data directory
    (e.g. "D:\\Data\\John.Smith@example.com") are assumed to be email
    addresses which can be used to match MyTardis user accounts.  If you wish
    to use email addresses as folder names, an alternative is to use the
    "Username / Experiment / Dataset" folder structure and use email
    addresses for usernames in MyTardis.  Folders inside each email folder (e.g.
    "D:\\Data\\John.Smith@example.com\\Experiment1" will be mapped to
    MyTardis experiments.  Folders inside each experiment folder
    (e.g. "D:\\Data\\John.Smith@examples.com\\Experiment1\\Dataset1")
    will be mapped to MyTardis datasets.

**Folder Structure - Username / "MyTardis" / Experiment / Dataset**
    Folders immediately inside the main data directory
    (e.g. "D:\\Data\\jsmith") are assumed to be MyTardis usernames.
    Folders inside each "MyTardis" folder
    (e.g. "D:\\Data\\jsmith\\MyTardis\\Experiment1" will be mapped to
    MyTardis experiments.
    Folders inside each experiment folder
    (e.g. "D:\\Data\\jsmith\\MyTardis\\Experiment1\\Dataset1") will be
    mapped to MyTardis datasets.

**Folder Structure - User Group / Instrument / Full Name / Dataset**
    Folders immediately inside the main data directory
    (e.g. "D:\\Data\\SmithLab") are assumed to be MyTardis user groups.
    The actual group name in MyTardis (e.g. "TestFacility-SmithLab")
    may have a prefix (e.g. "TestFacility-") prepended to it,
    specified by the "User Group Prefix" field below.
    Each user group folder should contain exactly one folder
    (e.g. "D:\\Data\\SmithLab\\Nikon Microscope #1") specifying the name
    of the instrument.  Using this scheme allows copying data from multiple
    instruments to a file share with the instrument name folder allowing users
    to distinguish between datasets from different instruments on the file
    share.
    Folders inside each instrument folder
    (e.g. "D:\\Data\\SmithLab\\Nikon Microscope #1\\John Smith") indicate
    the name of the researcher who collected the data or the researcher who
    owns the data.  Access control in MyTardis will be determined by the
    user group ("Smith Lab"), whereas the researcher's full name
    will be used to determine the default experiment (dataset grouping) in
    MyTardis.
    Folders inside each full name folder
    (e.g. "D:\\Data\\SmithLab\\Nikon Microscope #1\\John Smith\\Dataset1")
    will be mapped to MyTardis datasets.

**Folder Structure - Experiment / Dataset**
    Folders immediately inside the main data directory
    (e.g. "D:\\Data\\Experiment1") will be mapped to MyTardis experiments.
    Folders inside each experiment folder
    (e.g. "D:\\Data\\Experiment1\\Dataset1") will be mapped to MyTardis
    datasets.  This folder structure is designed for a data collection
    facility which is primarily staff-operated (not user-operated), so
    instead of creating a folder for each user, an 'experiment' folder
    is used to group datasets which should be accessible by the same
    group of researchers.

**Folder Structure - Dataset**
    Folders immediately inside the main data directory
    (e.g. "D:\\Data\\Dataset1") will be mapped to MyTardis datasets.
    Datasets will be automatically grouped into MyTardis experiments according
    to the "Experiment (Dataset Grouping)" field below.  This folder
    structure is designed for a facility using inflexible data collection
    software making it difficult to structure folders according to who should
    have access to them.

**Folder Structure - User Group / Experiment / Dataset**
    Folders immediately inside the main data directory
    (e.g. "D:\\Data\\SmithLab") are assumed to be MyTardis user groups.
    Folders inside each user group folder (e.g. "D:\\Data\\SmithLab\\Experiment1"
    will be mapped to MyTardis experiments.  Folders inside each experiment
    folder (e.g. "D:\\Data\\SmithLab\\Experiment1\\Dataset1") will be
    mapped to MyTardis datasets.

**Validate Folder Structure**
  When this is checked, MyData will ensure that the folders provided appear
  to be in the correct structure, and it will count the total number of
  datasets.  This can be disabled if you have a large number of dataset
  folders and slow disk access.

**Experiment (Dataset Grouping)**
  Defines how datasets will be grouped together into experiments in MyTardis.
  Currently, this field is automatically populated when you select a folder
  structure (above), and cannot be modified further.

**User Group Prefix**
  Used with the "User Group / Instrument / Full Name / Dataset"
  folder structure.
  Folders immediately inside the main data directory
  (e.g. "D:\\Data\\SmithLab") are assumed to be MyTardis user groups.
  The actual group name in MyTardis (e.g. "TestFacility-SmithLab")
  may have a prefix (e.g. "TestFacility-") prepended to it.

**Max # of upload threads**
  The maximum number of uploads to perform concurrently.  If greater than one,
  MyData will spawn multiple scp (secure copy) processes which (for large
  datafiles) may impact significantly on CPU usage of your system, which could
  affect other applications running alongside MyData.  The default value is 5.

**Max # of upload retries**
  The maximum number of times to retry uploading a file whose upload initially
  fails, e.g. due to a connection timeout error.

**Start automatically on login**
    As of v0.7.0-beta6, this checkbox is now disabled (read only) on Windows,
    because MyData is configured to start automatically for all users (if using
    MyData's setup wizard's default options) when it is first installed. Then
    it is up to the system administrator to decide whether to leave the MyData
    shortcut in
    C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\

    On Mac and Linux, MyData configures itself to start automatically on login
    only for the current user, based on the value of this checkbox.

    On Mac OS X, a login item will be created in the user's
    ~/Library/Preferences/com.apple.loginitems.plist which can be accessed from
    System Preferences, Users & Groups, Login Items.

    On Linux, MyData.desktop will be copied to ~/.config/autostart/ if this
    checkbox is ticked.

**Upload invalid user folders**
    If MyData finds a user (or group) folder which doesn't match a user (or group) on
    the MyTardis server, it can be configured to upload the data anyway (and assign it
    to the facility role account) by leaving this checkbox ticked.  Or the checkbox can
    be unticked if you want MyData to ignore user folders which can't be mapped to users
    or groups on the MyTardis server.


Locking and Unlocking MyData's Settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
At the bottom of MyData's Setting dialog is a Lock/Unlock button, whose label
toggles between "Lock" and "Unlock" depending on whether the Settings dialog's
fields are editable or read-only.  When the Settings dialog's fields are
editable, clicking the "Lock" button will make them read-only, preventing any
further changes to MyData's settings until an administrator has unlocked the
settings.  The locked status will persist after closing and relaunching MyData.

Clicking the "Lock" button displays the confirmation dialog below.

  .. image:: images/LockSettingsConfirmation.PNG

Once MyData's settings are locked, all of the fields in the Settings dialog
will become read-only.

  .. image:: images/SettingsLocked.PNG

Clicking on the "Unlock" button will result in a request for administrator
privileges.

  .. image:: images/UACElevation.PNG

Once administrator privileges have been verified, it will be possible to modify
MyData's settings again.

N.B. This is NOT a security mechanism - it is a mechanism for preventing the
accidental modification of settings in a production workflow.  It does not
prevent advanced users from determining where MyData saves its last used
configuration to disk (e.g. C:\\ProgramData\\Monash University\\MyData\\MyData.cfg)
and updating the settings outside of MyData.


.. _settings-saving-loading:

Saving and Loading Settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Each time you click OK on the Settings Dialog, your settings are validated, and
then saved automatically to a location within your user home folder, which is
OS-dependent, e.g. "C:\\ProgramData\\Monash University\\MyData\\MyData.cfg" or
"/Users/jsmith/Library/Application Support/MyData/MyData.cfg".

The settings file is in plain-text file whose format is described here:
https://docs.python.org/2/library/configparser.html.  An example can be
found here:
`MyDataDemo.cfg <https://github.com/monash-merc/mydata-sample-data/releases/download/v0.1/MyDataDemo.cfg>`_.

Any facilities with potentially malicious users may wish to consider what
happens if a user gets hold of an API key for a facility role account, saved
in a MyData configuration file.  The API key cannot be used in place of a
password to log into MyTardis's web interface, but it can be used with
MyTardis's RESTful API to gain facility manager privileges.  These privileges
would not include deleting data, but for a technically minded user familiar
with RESTful APIs, the API key could potentially be used to modify another
user's data.  Facilities need to decide whether this is an acceptable risk.
Many facilities already use shared accounts on data-collection PCs, so the
risk of one user modifying another user's data subdirectory is already there.

Settings can be saved to an arbitrary location chosen by the user by clicking
Control-s (Windows) or Command-s (Mac OS X) from MyData's Settings dialog,
keeping in mind the risks stated above.  A saved settings file can then be
dragged and dropped onto MyData's settings dialog to import the settings.
This feature is currently used primarily by MyData developers for testing
different configurations.  It is expected that the MyData settings for each
individual instrument PC will remain constant once the initial configuration
is done.


Settings only configurable in MyData.cfg
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The following settings do not appear in the Settings Dialog, but can be
configured directly in MyData.cfg, which is typically found at a location
like:
"C:\\ProgramData\\Monash University\\MyData\\MyData.cfg" or
"/Users/jsmith/Library/Application Support/MyData/MyData.cfg".

You should exit MyData before modifying MyData.cfg, and then restart it after
saving your changes to MyData.cfg.

The "verification" in "max_verification_threads" below refers to the DataFile
lookups performed by MyData to determine whether each local file has been
previously uploaded to and verified on the MyTardis server, whereas the
"verification" in "verification_delay" refers to MyData's request for MyTardis
to verify that a newly uploaded file has the correct size and checksum.

    +--------------------------+-----------------------------------+--------------------------------------------------------+
    | Setting                  | Default value                     | Description                                            |
    +==========================+===================================+========================================================+
    | max_verification_threads | 5                                 | Maximum number of concurrent DataFile lookups          |
    +--------------------------+-----------------------------------+--------------------------------------------------------+
    | verification_delay       | 3                                 | Upon a successful upload, MyData will request          |
    |                          |                                   | verification after a short delay (e.g. 3 seconds)      |
    +--------------------------+-----------------------------------+--------------------------------------------------------+
    | immutable_datasets       | False                             | Whether datasets created by MyData should be read-only |
    +--------------------------+-----------------------------------+--------------------------------------------------------+
    | progress_poll_interval   | 1                                 | Interval in seconds between RESTful progress queries   |
    +--------------------------+-----------------------------------+--------------------------------------------------------+
    | cipher                   | aes128-gcm@openssh.com,aes128-ctr | Encryption cipher for SCP uploads                      |
    +--------------------------+-----------------------------------+--------------------------------------------------------+
    | use_none_cipher          | False                             | Use None cipher (only applicable for HPN-SSH)          |
    +--------------------------+-----------------------------------+--------------------------------------------------------+
    | fake_md5_sum             | False                             | Skip MD5 calculation, and just send a string of zeroes |
    +--------------------------+-----------------------------------+--------------------------------------------------------+

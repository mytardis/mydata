Settings
========

General
^^^^^^^

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

Advanced
^^^^^^^^

**Folder Structure - Username / Dataset**
    Folders immediately inside the main data directory
    (e.g. "D:\\Data\\jsmith") are assumed to be MyTardis usernames.
    Folders inside each user folder (e.g. "D:\\Data\\jsmith\\Dataset1"
    will be mapped to MyTardis datasets.
    Datasets will be automatically grouped into MyTardis experiments according
    to the "Experiment (Dataset Grouping)" field below.

**Folder Structure - Email / Dataset**
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

**Ignore datasets older than**
  MyData is designed to be used for uploading recent data.  If it is configured
  to use an existing data directory containing a large backlog of old data, it
  is advisable to instruct MyData to ignore old datasets so that it focus on
  uploading the recent datasets.

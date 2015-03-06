User Groups
===========

Assigning access to datasets to user groups is an alternative to assigning
access to individual users.  A folder structure of
"User Group/Instrument/Data Owner Full Name/Dataset" is supported for this
purpose.  As well as being used by MyData, this folder structure can be used
to copy / sync data to a shared network drive.  Each instrument PC will only
have one instrument folder, being the name of that instrument, but when data
from multiple instrument PCs is copied to the shared network drive, multiple
instrument folders can appear alongside each other.  The "Data Owner Full Name"
folder is usually the name of the person who collected the data, but it is
really just a way of grouping datasets into MyTardis experiments, i.e. it is
not used to assign access control.

For more information, see the
"Folder Structure - User Group / Instrument / Full Name / Dataset" section in
http://mydata.readthedocs.org/en/latest/settings.html#advanced

Data Uploads from Instrument PCs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When using User Groups, the primary data directory used with MyData could look
like this:

  .. image:: images/UserGroups.PNG

The first folder level within C:\\UserGroups ("Group1", "Group2" etc.) is a
user group defined in MyTardis.  The actual group names in MyTardis may have
an additional prefix ("TestFacility-") prepended to the folder name, i.e. 
"TestFacility-Group1", "TestFacility-Group2" etc. 

The second folder level within C:\\UserGroups ("Instrument 1") is the name of
the data collection instrument.  This folder may seem redundant, because all of
the data on each instrument PC is by definition, on the same instrument PC
(e.g. "Instrument 1"), but this folder level becomes useful when data from
multiple instrument PCs is synced to a shared network drive.

The third folder level within C:\\UserGroups ("G1Member1", "G1Member2",
"G2Member1", "G2Member2" etc.) is usually the full name of the researcher who
owns the data, but in some cases it is just an arbitrary collection of
datasets.  This corresponds to an experiment in MyTardis, which is a collection
of datasets which can be made accessible to a particular user or to a group
(e.g.  "TestFacility-Group1").

The fourth folder level within C:\\UserGroups ("Dataset001" etc.) is mapped to
a MyTardis dataset.

  .. image:: images/GroupsInMyData.PNG

The MyData screenshot shows the 8 datasets found within the C:\\UserGroups
directory on the "Instrument 1" PC.  MyData counts the number of files
within each dataset folder on the local disk, then counts the number of files
previously uploaded to VicNode / MyTardis for that dataset (if any), and then
uploads any datafiles which are not already available on VicNode / MyTardis.

Whilst MyData can recognize old data in a well-defined folder structure as
described above, MyData is generally intended to be used to upload recently
acquired data.  An option to ignore old datasets (older than 6 months) has
recently been implemented in MyData.

Data Management in MyTardis for Facility Managers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The first time MyData is run on a new instrument PC, some configuration is
required - MyDatas Settings dialog is shown below.  Typically a facility role
account in MyTardis ("testfacility" in this case) is used to upload data).
Once the data has been uploaded, access (and ownership) can be granted to
individual users within MyTardis.  In the case of the User Group folder
structure, MyData will attempt to automatically grant read access to each
dataset to all users within the data set's user group (e.g.
"TestFacility-Group1").

  .. image:: images/SettingsGeneralUserGroups.PNG

  .. image:: images/SettingsAdvancedUserGroups.PNG  

The "testfacility" account in this MyTardis instance is associated with a
facility record in MyTardis's database, which means that MyTardis's Facility
Overview will be accessible when logged into MyTardis as "testfacility".  The
Facility Overview lists recently uploaded datasets.  The number of verified
files in each dataset is the number of files which have been uploaded and
confirmed to have the correct file size and MD5 checksum.

  .. image:: images/FacilityOverviewUserGroups.PNG

User and Group Management in MyTardis for Facility Managers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The "testfacility" account in this MyTardis instance is a group administrator
for the "TestFacility-Group1" group, which means that they can view all members
of that group by selecting Group Management from the drop-down menu available
by clicking on the "testfacility" username in the upper-right corner of
MyTardis.

  .. image:: images/GroupManagement.PNG

Clicking on an experiment from the Facility Overview page (or from the My Data
page or from the Home page) allows you to determine which users its datasets
are accessible to.  In this case, the "Instrument 1 - G1Member1" experiment is
owned by "testfacility" and is accessible by the "TestFacility-Group1" group.
Users can be granted access (or revoked access) using the Change User Sharing
and Change Group Sharing buttons.

  .. image:: images/ExperimentInMyTardisFromGroupFolderStructure.PNG

Researchers can log into MyTardis and view all experiments which their user
group has access to.  User "wettenhj" has access to the experiment
"Instrument 1 - G1Member1" (below), because he is a member of the
"TestFacility-Group1" group. 

  .. image:: images/ExperimentAccessViaGroup.PNG


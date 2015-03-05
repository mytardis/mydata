Mac OS X Walkthrough
====================

MyData development is primarily targeting Windows, which is the OS of choice
for most data-collection instrument PCs.  This document aims to demonstrate 
that MyData can also run on Mac OS X.

On Mac OS X, after downloading and opening the disk image (DMG) file, drag the
MyData application into your Applications folder and launch it.  (You can then
eject the disk image.)

  .. image:: images/MyDataDmg.png

A test MyTardis site is available for authorized MyData testers.  Contact
James Wettenhall at James.Wettenhall@monash.edu.au if you would like to
register for testing MyData against this MyTardis test site or if you would
like assistance with setting up an alternative test site for MyData.
After registering as an authorized MyData tester, you will receive a MyTardis username and password.  In my case, my MyTardis username is "wettenhj".  

Choose a folder where you would like to store your data.  I chose
"/Users/Shared/MyDataTest":

  .. image:: images/DataDirectory.png

Create a folder whose name matches your MyTardis username ("wettenhj" for me):

  .. image:: images/UserFolder.png

Put your data within your user folder, ensuring that all datafiles are grouped
within folders, which will become datasets in MyTardis:

  ..image:: images/DatasetsInUserFolder.png

Launch MyData, and enter some basic settings in MyData's Settings dialog
(below).

  .. image:: images/SettingsDialogMacOSX.png

Starting MyData's Scan and Upload Processes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
MyData will scan for data and attempt to upload it as soon as you click "OK"
on the Settings dialog or whenever you press the refresh icon on MyData's
toolbar.  If you launch MyData with a "--background" command-line argument,
then it will automatically begin its scan and upload processes straight away,
even without displaying its Settings dialog, assuming that valid settings have
been entered previously.

MyData's Upload Methods
^^^^^^^^^^^^^^^^^^^^^^^
MyData supports two upload methods - HTTP POST and SCP via staging.

The HTTP POST upload method is only intended to be used for quick demos and for
small data files.  Uploading large files with HTTP POST can put significant
strain on the MyTardis server's resources (particularly memory usage).  The
only advantage of HTTP POST is that it is easy to configure.  As long as you
have access to a suitable MyTardis role account (e.g. "testfacility") and know
its API key, then you can begin uploading from MyData straight away, although
you should begin by testing small files only.

SCP via staging is MyData's preferred upload method.  MyData will automatically
use this method as soon as it become available, but uploads via staging need to
be approved by a MyTardis administrator.  MyData generates an SSH key pair the
first time it runs and sends the public key to the MyTardis server in a request
for the ability to upload via staging.  The MyTardis administrator needs to
approve the request and put the public key in a suitable authorized keys file
on the staging server (which could be the same as the MyTardis server).  For
example, the public key could be put in "/home/mydata/.ssh/authorized_keys" on
the staging server.

The first time a user runs MyData, they wil see a warning indicating that
MyData's preferred upload method (SCP via staging) hasn't yet been approved by
the MyTardis administartor:

  .. image:: images/UploadsToStagingRequireApprovalWarning.png

The MyTardis administrator can approve the request in the Django Admin
interface (after adding the public key to the appropriate
/home/mydata/.ssh/authorized_keys file):

  .. image:: images/UploaderRegistrationApproval.png

Once uploads to staging have been approved, MyData can manage multiple uploads
at once (5 by default):

  .. image:: images/MultipleUploadThreads.png

By clicking on the web browser icon on MyData's toolbar, you can view the
uploaded data in MyTardis in your web browser.  The data will be jointly owned
by the facility role account (e.g. "testfacility") and by the MyTardis user
whose username (e.g. "wettenhj") was used to name the folder containing the
datasets.  MyTardis allows grouping datasets together into experiments.  MyData
uses the instrument name (e.g. "James Mac Laptop") and the date of creation of
the dataset folders (e.g. "2014-12-18") to define a default experiment for the
datasets it uploads:

  .. image:: images/DataInMyTardis.png

If you are authorized to log into MyTardis's web interface as a facility
manager, you can view the data in MyTardis's new Facility Overview.  Note the
two owners - the facility role account ("testfacility") and the individual user
("wettenhj") who collected the data:

  .. image:: images/FacilityOverview.png


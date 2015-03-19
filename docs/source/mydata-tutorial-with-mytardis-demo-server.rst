MyData Tutorial, using the MyTardis Demo Server
===============================================

Downloading and Installing the MyTardis Demo Server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Download the MyTardis Demo Server for Windows:

  + `MyTardisDemoServer_d82f585c35c187cac0110adc13d29ff1a963dab2.exe <https://github.com/monash-merc/mydata/releases/download/v0.2.0-beta1/MyTardisDemoServer_d82f585c35c187cac0110adc13d29ff1a963dab2.exe>`_

After downloading the MyTardis Demo Server, open the downloaded executable to
begin the setup wizard, which shows the version of MyTardis being installed
(from the https://github.com/wettenhj/mytardis/tree/mydata branch):

  .. image:: images/MyTardisDemoServerSetupWizardPage1.PNG

The default installation location is C:\\MyTardisDemoServer:

  .. image:: images/MyTardisDemoServerSetupWizardPage2.PNG


Launching the MyTardis Demo Server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
After installing the MyTardis Demo Server (which could takes 5-10 minutes),
start the MyTardis server by clicking the "MyTardis Demo Server" shortcut in
the Start Menu (or in the Start Screen if you don't have a Start Menu):

  .. image:: images/MyTardisDemoServerStartMenu.PNG

The MyTardis Demo Server will display a Command Prompt window starting in the
installed directory (defaulting to C:\\MyTardisDemoServer), and then navigating
into the specific MyTardis version directory (e.g.
C:\\MyTardisDemoServer\\d82f585c35c187cac0110adc13d29ff1a963dab2) and then
running the demo server (using "python mytardis.py runserver").  The MyTardis
Demo Server bundles its own version of Python and puts it in the PATH before
any other Python version you may have installed while running this Command
Prompt window (see C:\\MyTardisDemoServer\\MyTardisDemoServer.bat).

  .. image:: images/MyTardisDemoServerStarting.PNG


Accessing the MyTardis Demo Server in your web browser
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once the MyTardis Demo Server has started, you can access its web interface
by navigating to the following address:  http://127.0.0.1:8000/ in your web
browser (Google Chrome is a good choice).

  .. image:: images/MyTardisDemoServerChrome.PNG


Logging into the MyTardis Demo Server as a MyTardis administrator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Click the "Log In" button in the upper right corner, and log in with username
"mytardis" and password "mytardis".

  .. image:: images/MyTardisDemoServerLoggingInAsMyTardis.PNG

**Accessing MyTardis's Django Admin Interface**

The "mytardis" account in this demo server is a super administrator, i.e. it
can do anything, including accessing MyTardis's Django Admin interface from
the menu item shown below.

  .. image:: images/MyTardisDemoServerAdminAccess.PNG

MyTardis's Django Admin interface looks similar to many other Django
applications' admin interfaces.  Keep in mind that this interface is extremely
powerful, so if you are not careful, you could delete database records without
any way to recover them!

  .. image:: images/MyTardisDemoServerAdminInterface.PNG

**Facilities Registered in MyTardis**

From the Django Admin interface, click on "Facilities" to see what facilities
are available in this Demo Server.  There is only one facility, named
"Test Facility".

  .. image:: images/MyTardisDemoServerFacilities.PNG

Click on the "Test Facility" facility record to see the properties of the
facility, including the "Test Facility Managers" user group assigned to the
"Manager group" field of the facility record.

  .. image:: images/MyTardisDemoServerTestFacility.PNG

**User Accounts in MyTardis**

From the Django Admin interface, click on Users to see the user accounts
available in this MyTardis server.  The "mytardis" administrator is the only
account which can access the Django Admin interface.

  .. image:: images/MyTardisDemoServerUsers.PNG

Click on the "testfacility" user account to see its attributes.  Note that this
account is a member of the "Test Facility" facility record's manager group,
named "Test Facility Managers".

  .. image:: images/MyTardisDemoServerTestFacilityUserAccount.PNG


Logging into the MyTardis Demo Server as a MyTardis facility manager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Log out of the Django Admin interface, and then return to the original URL
in your web browser's address bar, i.e. http://127.0.0.1:8000/, not
http://127.0.0.1:8000/admin/.  Then log in with username "testfacility" and
password "testfacility", and click on the "Facility Overview" section link in
the navigation bar at the top of the MyTardis home page.  Since we haven't
uploaded any data yet, no data will appear in the Facility Overview, but we
can confirm that the "testfacility" account has access to the Facility Overview
for the "Test Facility" facility.

  .. image:: images/MyTardisDemoServerFacilityOverviewNoData.PNG


Obtaining the demo data
^^^^^^^^^^^^^^^^^^^^^^^

Download `MyTardisDemoData.zip <https://github.com/monash-merc/mydata-sample-data/releases/download/v0.1/MyTardisDemoData.zip>`_ in extract it in "C:\\" to create
the "C:\\MyTardisDemoUsers" folder shown below:

  .. image:: images/MyDataDemoDataWindowsExplorer.PNG


Launching MyData
^^^^^^^^^^^^^^^^

MyData can be downloaded from here: http://mydata.readthedocs.org/en/latest/download.html

Open the downloaded executable and proceed through the setup wizard to install
MyData.  A shortcut to MyData will then be available in the Start Menu (or the
Start Screen if not using a Start Menu):

  .. image:: images/MyDataInStartMenu.PNG

When you launch MyData interactively (which is the default, unless you give
MyData.exe a command-line argument of "--background"), its settings dialog
will appear automatically.  The first time you launch MyData, its settings
will be blank:

  .. image:: images/MyDataSettingsBlank.PNG


.. _demo-configuration-download:

Downloading and installing the demo configuration for MyData
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Download `MyDataDemo.cfg <https://github.com/monash-merc/mydata-sample-data/releases/download/v0.1/MyDataDemo.cfg>`_ onto your Desktop and drag and drop it onto
MyData's settings dialog, which should automatically populate the fields in
MyData's settings dialog.

  .. image:: images/SettingsDialogDemoSettings.PNG

The Advanced tab of MyData's settings dialog contains additional settings:

  .. image:: images/SettingsDialogAdvancedDemoSettings.PNG


MyData's Settings Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After clicking "OK" on the settings dialog, MyData will validate the settings
and inform the user of any problems it finds.  When running in interactive
mode, MyData will then inform the user of how many datasets it has counted
within the data directory and ask the user to confirm that they want to
continue.

  .. image:: images/MyDataDemoNumberOfDatasetsConfirmation.PNG



MyData's Upload Methods
^^^^^^^^^^^^^^^^^^^^^^^

MyData offers two upload methods:

* HTTP POST
* SCP to Staging

The second method ("SCP to Staging") can handle much larger datafiles and
supports multiple concurent upload threads, however it is slightly more
complicated to set up, so we won't be covering it in this tutorial.  Instead,
we will stick with MyData's default upload method ("HTTP POST") and ignore
the warning dialog below.

  .. image:: images/MyDataHttpPostWarning.PNG


MyData's Folders View
^^^^^^^^^^^^^^^^^^^^^

MyData's Folders view lists all of the dataset folders which will be scanned
for files to upload to MyTardis.  For each folder, MyData displays a count
of the total number of files in that folder, and the number of files which
have already been uploaded to MyTardis.  MyData is stateless, i.e. it won't
remember how many files were confirmed to be on MyTardis last time it was
run, so each count will begin at zero and then increment by one as each file
is confirmed to be available on MyTardis.

  .. image:: images/MyDataDemoDataFoldersView.PNG


MyData's Users View
^^^^^^^^^^^^^^^^^^^

MyData's Users view (below) displays the result of MyData's attempt to map the
user folder names ("testuser1" and "testuser2") to MyTardis user accounts.  In
this case, both user folder names have been successfully mapped to user
accounts on our MyTardis Demo Server, but no email address has been recorded
for either account in MyTardis.  Many queries MyData performs against MyTardis
will only work if the MyTardis account you entered in MyData's settings dialog
("testfacility") has sufficient permissions assigned to it, as shown on the
`Django Admin's user account attributes page for the "testfacility" account <_images/MyTardisDemoServerTestFacilityUserAccount.PNG>`_.  In this case, the
"testfacility" account can access other users' email addresses because it is
a member of a Facility Managers group in MyTardis.

  .. image:: images/MyDataDemoDataUsersView.PNG


MyData's Verifications View
^^^^^^^^^^^^^^^^^^^^^^^^^^^

MyData's Verifications view (below) shows MyData's attempts to verify whether
each datafile is available on the MyTardis server, or whether it needs to be
uploaded.

  .. image:: images/MyDataDemoDataVerificationsView.PNG


MyData's Uploads View
^^^^^^^^^^^^^^^^^^^^^

MyData's Uploads view (below) shows MyData's upload progress.  The default
HTTP POST method only supports one concurrent upload, whereas the
"SCP to Staging" upload method supports multiple concurrent uploads.

  .. image:: images/MyDataDemoDataUploadsView.PNG


Monitoring MyData Uploads in MyTardis's Facility Overview
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After some of the datafiles have completed uploading, you can check back
in your web browser to see the datafiles in MyTardis's Facility Overview
(below).  You should be logged into MyTardis as the "testfacility" account
(username "testfacility", password "testfacility").

For the demo server, we are using the `CELERY_ALWAYS_EAGER <http://celery.readthedocs.org/en/latest/configuration.html#celery-always-eager>`_ setting
which means that datafiles will be verified immediately, instead of as a
background task.  This explains why the number of verified datafiles below
is always equal to the total number of datafiles for each dataset.  In the
screenshot below, only 6 datafiles have been uploaded from the
"Amorphophallus Titanum SEM" dataset, and no datafiles have been uploaded
from the other datasets yet.

  .. image:: images/MyTardisDemoServerFacilityOverviewOneDatasetUploaded.PNG


MyTardis's "My Data" View from a Facility Manager's Perspective
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

While logged in as "testfacility" (an account whose credentials could be
shared amongst the managers of "Test Facility"), click on "My Data" to see
all of the "experiments" (dataset collections) created by MyData while running
at that facility.  MyData's default dataset grouping uses the instrument name
("Test Microscope") and the user's full name (e.g. "Test User1") to define
a MyTardis "experiment" record, as seen in MyTardis's "My Data" view below.

  .. image:: images/MyTardisDemoServerTestFacilityMyData.PNG

MyTardis from a Facility User's Perspective
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Log out of MyTardis, and log back in with the username "testuser1" and password
"testuser1".  Now you only see the data collected by user "testuser1", not
the data collected by "testuser2".  The "Test User1" in the experiment (dataset
group) names may seem redundant here, but users can share their experiments
with other users, so it would be confusing if all of the shared experiments
were just given a default name of "Test Microscope".

  .. image:: images/MyTardisDemoServerTestUser1Home.PNG

Click on the "Test Microscope - Test User1" experiment to see the datasets
included in that experiment:

  .. image:: images/MyTardisDemoServerTestUser1Experiment1.PNG

Click on the "Amorphophallus Titanum SEM Dataset" to see the datafiles in
that dataset:

  .. image:: images/MyTardisDemoServerAmorphophallusTitanumSemDataset.PNG



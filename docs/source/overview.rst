Overview
========

MyData is a desktop application for uploading data to MyTardis
(https://github.com/mytardis/mytardis).  It allows users of a data-collection
instrument to have their data automatically uploaded to MyTardis simply by
saving their data in a pre-defined folder structure.  The simplest folder
structures available is "Username / Dataset", which is described below.

We begin with a root data directory (e.g. "C:\\MyTardisUsers") containing one
folder for each MyTardis user.  In the example below, we have two users with
MyTardis usernames "testuser" and "wettenhj".

  .. image:: images/UserFolders.PNG

Within each user folder, we can add as many folders as we like, and each one
will become a "dataset" within MyTardis:

  .. image:: images/Datasets.PNG

MyData is designed to be able to run interactively or in the background.
Once its settings have been configured, it minimizes itself to the system
tray (Windows) or menubar (Mac OS X) and runs the data scan and upload
task according to a scheduled configured by the user.  Many data-collection
instrument PCs use a shared login account which remains logged
in all day long.  MyData at present cannot run as a
`service daemon <http://en.wikipedia.org/wiki/Daemon_%28computing%29>`_
- so it will not run while no users are logged in.

The first time you run MyData, you will be asked to enter some settings,
telling the application how to connect to your MyTardis instance.  You can use
a MyTardis account which is shared amongst facility managers, but which general
users don't have access to.

  .. image:: images/SettingsGeneral.PNG

  .. image:: images/SettingsAdvanced.PNG

Each time the application starts up (and when you tell it to), it will scan all
of the user and datset folders within your primary data directory (e.g.
C:\\MyTardisUsers) and present a list of all of the dataset folders in a
tabular view (below).  MyData will count the number of files within each
dataset folder (including nested subdirectories), and then query MyTardis to
determine how many of these files have already been uploaded.  If MyData finds
new files which haven't been uploaded, it will begin uploading them (with a
default maximum of 5 simultaneous uploads).  You can see progress of the
uploads in the "Uploads" tab.

  .. image:: images/FoldersView.PNG

Closing MyData's main window will minimize the MyData application to an
icon in the System Tray (below).  It is possible to exit MyData using a
menu item from the System Tray icon's pop-up menu (further below), but
exiting will prevent MyData from being able to run scheduled tasks.

  .. image:: images/SystemTrayIcon.PNG

Clicking on MyData's System Tray icon will bring up a menu, allowing you to
restore MyData's main window (the "Control Panel") or "Sync Now"
to ensure that new data is uploaded promptly:

  .. image:: images/SystemTrayMenu.PNG

You can tell when MyData has finished uploading a dataset by looking at the
number of files uploaded in the Status column of the Folders view. Then you can
select that dataset's row in the Folders view and click on the "Web Browser"
icon to view that dataset in MyTardis.

MyTardis uses "experiments" to organize collections of datasets.  When using
the default "Username / Dataset" folder structure, the default name for each
experiment created by MyData will be the instrument name
(e.g. "Test Microscope"), followed by the data owner's full name (if it can be
retrieved from MyTardis using the username given as a folder name).

The experiment will initially be owned by the facility manager user specified
in MyData's Settings dialog (e.g. "testfacility"). MyData will then use
MyTardis's ObjectACL's (access control lists) to share ownership with the
individual researcher (e.g. "wettenhj" or "skeith") who must have a MyTardis
account. Below we can see the experiments created by MyData as owned by the
facility manager user ("testfacility").

  .. image:: images/MyTardisDefaultUser.PNG

And below, we can see user wettenhj's data - note that "wettenhj" is now the
logged-in MyTardis user in the upper-right corner, instead of "testfacility".

  .. image:: images/MyTardisActualUser.PNG


MyData User Guide
=================

**1. Overview**  
**2. MyTardis Prerequisites**  

1. Overview
-----------
MyData is a desktop application (initially targeting Windows) for uploading data to MyTardis (https://github.com/mytardis/mytardis).

We begin with a root data directory (e.g. "C:\MyTardisUsers") containing one folder for each MyTardis user.  In the example below, we have two users with MyTardis usernames "skeith" and "wettenhj".
<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/User%20Folders.PNG" alt="User Folders" style="width: 200px;"/>

Within each user folder, we can add as many folders as we like, and each one will become a "dataset" within MyTardis:

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/Datasets.PNG" alt="Datasets" style="width: 200px;"/>

The MyData application (which can be downloaded from here: https://github.com/wettenhj/mydata/raw/master/UserGuideImages/MyData_v0.0.2.exe) can be configured to start up automatically each time Windows starts up.  (The current proposed deployment site switches off their microscope PCs every night and turns them back on in the morning.)  The first time you run the application, you will be asked to enter some settings, telling the application how to connect to your MyTardis instance.  You can use a MyTardis account which is shared amongst facility managers, but which general users don't have access to:

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/Settings.PNG" alt="Settings" style="width: 200px;"/>

Each time the application starts up (and when you tell it to), it will scan all of ther user and dataset folders within your primary data directory (e.g. C:\MyTardisUsers), and present a list of all of the dataset folders in a tabular view (below).  MyData will count the number of files within each dataset folder (including nested subdirectories), and then query MyTardis to determine how many of these files have already been uploaded.  If MyData finds new files which haven't been uploaded, it will begin uploading them (with a default maximum of 5 simultaneous upload threads).  You can see progress of the uploads in the "Uploads" tab.

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/MyData%20Folders.PNG" alt="MyData Folders" style="width: 200px;"/>

The MyData application is intentionally difficult to shut down.  It is designed to be shut down only by facility managers, not by an individual researcher.  Closing the main window will minimize the MyData application to an icon in the System Tray (below).  It is possible to exit MyData using a menu item from the System Tray icon's pop-up menu (further below), but upon clicking on this menu item, the user will be asked for administrator privileges.

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/System%20Tray%20Icon.PNG" alt="System Tray Icon" style="width: 200px;"/>

Clicking on MyData's System Tray icon will bring up a menu, allowing you to restore MyData's main window (the "Control Panel") or force a "MyTardis Sync" to ensure new data is uploaded promptly:

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/System%20Tray%20Menu.PNG" alt="System Tray Menu" style="width: 200px;"/>

You can tell when MyData has finished uploading a dataset by looking at the number of files uploaded in the Status column of the Folders view.  Then you can select that dataset's row in the Folders view and click on the "Web Browser" icon to view that dataset in MyTardis.

MyTardis uses "experiments" to organize collections of datasets.  The default name for each experiment created by MyData will be the instrument name (e.g. "Test Microscope #1"), followed by the data collection date (e.g. "2014-01-09").  The experiment will initially be owned by the facility manager user specified in MyData's Settings dialog (e.g. "mmi").  MyData will then use MyTardis's ObjectACL's (access control lists) to share ownership with the individual researcher (e.g. "wettenhj" or "skeith") who must have a MyTardis account.  Below we can see the experiments created by MyData as owned by the facility manager user ("mmi"):

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/MyTardis%20Default%20User.PNG" alt="MyTardis Default User" style="width: 200px;"/>

And below we can see user wettenhj's data - note that "wettenhj" is now the logged-in MyTardis user in the upper-right corner, instead of "mmi":

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/MyTardis%20Actual%20User.PNG" alt="MyTardis Actual User" style="width: 200px;"/>


2. MyTardis Prerequisites
-------------------------
* MyData is currently being developed against the "develop" branch of MyTardis, which uses version "v1" of MyTardis's RESTful API.  A few additions to MyTardis's RESTful API are required by MyData.  These additions can be found here: https://github.com/wettenhj/mytardis/compare/mytardis:develop...mydata
* MyData stores metadata for each experiment it creates (the instrument name, the researcher's MyTardis username and the date of collection):

<img src="https://github.com/wettenhj/mydata/raw/master/UserGuideImages/Experiment%20Schema%20and%20Parameter%20Names.PNG" alt="Experiment Schema and Parameter Names" style="width: 200px;"/>







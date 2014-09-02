MyData User Guide
=================

MyData is a desktop application (initially targeting Windows) for uploading data to MyTardis (https://github.com/mytardis/mytardis).

We begin with a root data directory (e.g. "C:\MyTardisUsers") containing one folder for each MyTardis user.  In the example below, we have two users with MyTardis usernames "skeith" and "wettenhj".
<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/User%20Folders.PNG" alt="User Folders" style="width: 200px;"/>

Within each user folder, we can add as many folders as we like, and each one will become a "dataset" within MyTardis:

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/Datasets.PNG" alt="Datasets" style="width: 200px;"/>

The MyData application (which can be downloaded from here: https://github.com/wettenhj/mydata/raw/master/UserGuideImages/MyData_v0.0.1.exe) can be configured to start up automatically each time Windows starts up.  (The current proposed deployment site switches off their microscope PCs every night and turns them back on in the morning.)  The first time you run the application, you will be asked to enter some settings, telling the application how to connect to your MyTardis instance.  You can use a MyTardis account which is shared amongst facility managers, but which general users don't have access to:

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/Settings.PNG" alt="Settings" style="width: 200px;"/>

Each time the application starts up (and when you tell it to), it will scan all of ther user and dataset folders within your primary data directory (e.g. C:\MyTardisUsers), and present a list of all of the dataset folders in a tabular view (below).  MyData will count the number of files within each dataset folder (including nested subdirectories), and then query MyTardis to determine how many of these files have already been uploaded.  If MyData finds new files which haven't been uploaded, it will begin uploading them (with a default maximum of 5 simultaneous upload threads).  You can see progress of the uploads in the "Uploads" tab.

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/MyData%20Folders.PNG" alt="MyData Folders" style="width: 200px;"/>

The MyData application is intentionally difficult to shut down.  It is designed to be shut down only by facility managers, not by the average users.  Closing the main window will minimize the MyData application to an icon in the System Tray:

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/System%20Tray%20Icon.PNG" alt="System Tray Icon" style="width: 200px;"/>

Clicking on MyData's System Tray icon will bring up a menu, allowing you to restore MyData's main window (the "Control Panel") or force a "MyTardis Sync" to ensure new data is uploaded promptly:

<img src="https://github.com/wettenhj/mydata/blob/master/UserGuideImages/System%20Tray%20Menu.PNG" alt="System Tray Menu" style="width: 200px;"/>





MyData Walkthrough
==================

Download MyData from [here](https://github.com/wettenhj/mydata/raw/master/UserGuideImages/MyData_v0.1.0.dmg) (Mac) or from [here](https://github.com/wettenhj/mydata/raw/master/UserGuideImages/MyData_v0.1.0.exe) (Windows).

On Mac OS X, after downloading and opening the disk image (DMG) file, drag the MyData
application into your Applications folder and launch it.  (You can then eject the disk
image.) 
<img src="https://github.com/monash-merc/mydata/blob/master/WalkthroughImages/MyDataDmg.png" alt="MyData DMG" style="width: 200px;"/>

A test MyTardis site for authorized MyData testers is available at http://118.138.241.91/.
Contact JW if you would like to register for testing MyData against this MyTardis test
site or if you would like assistance with setting up an alternative test site for MyData.
After registering as an authorized MyData tester, you will receive a MyTardis username and
password.  In my case, my MyTardis username is "wettenhj".

Choose a folder where you would like to store your data.  I chose "/Users/Shared/MyDataTest":
<img src="https://github.com/monash-merc/mydata/blob/master/WalkthroughImages/DataDirectory.png" alt="Data Directory" style="width:200px;"/>

Create a folder whose name matches your MyTardis username ("wettenhj" for me):
<img src="https://github.com/monash-merc/mydata/blob/master/WalkthroughImages/UserFolder.png" alt="User Folder" style="width:200px;"/>

Put your data within your user folder, ensuring that all datafiles are grouped within
folders, which will be become datasets in MyTardis:<br/>
<img src="https://github.com/monash-merc/mydata/blob/master/WalkthroughImages/DatasetsInUserFolder.png" alt="Data In User Folder" style="width:200px;"/>

Launch MyData, and enter some basic settings in MyData's Settings Dialog (below).  Each
field is described further below.<br/>
<img src="https://github.com/monash-merc/mydata/blob/master/WalkthroughImages/SettingsDialog.png" alt="Settings Dialog" style="width:200px;"/>

**Facility Name**

A facility record must have been created by your MyTardis administrator before you can use MyData.
For MyData testing purposes, we will use the "Test Facility" facility, available on
the http://118.138.241.91 MyTardis test site.

**Instrument Name**

MyData is targeting data-collection PCs, e.g. microscope PCs, but most MyData testers are
expected to use laptops which are not connected to any data-collection instrument.
So where you see "Instrument Name" in MyData, you can use something like "James Mac Laptop",
which can be used to distinguish your "pretend instrument PC" from other pretend
instrument PCs connecting to the same "Test Facility" in MyTardis.

Contact Name

MyData's preferred upload method (staging) requires approval from a MyTardis administrator.
This Contact Name will be used when sending confirmation that access to MyTardis's staging
area has been approved for this MyData instance.

Contact Email

MyData's preferred upload method (staging) requires approval from a MyTardis administrator.
This Contact Name will be used when sending confirmation that access to MyTardis's staging
area has been approved for this MyData instance.

Data directory

Choose a folder where you would like to store your data.  (I chose "/Users/wettenhj/Desktop/MyDataTest")

MyTardis URL

The URL of a MyTardis server running a MyTardis version compatible with MyData, e.g. http://118.138.241.91

MyTardis default username

DO NOT put your individual MyTardis username (e.g. "wettenhj") in here.  Because MyData is 
designed to be able to upload multiple users' data from a instrument PC, the default username
used by MyData should generally be a shared facility role account.  For testing against 
http://118.138.241.91, we will use "testfacility".  Contact JW if you want the password for
this test account.

MyTardis API key

API keys are similar to passwords, but they are easier to revoke and renew when necessary.
Ask your MyTardis administrator for the API key corresponding to your facility role account.
Or if using the "testfacility" account with http://118.138.241.91, contact JW to obtain
the API key for that account.


WARNING: Uploads require approval.

Show dialog.  Explain.

Explain Refresh. Show multiple upload threads.

Show web browser toolbar icon, show data in MyTardis.

Show data in facility view.  Note the two owners.



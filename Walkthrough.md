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

**Contact Name**

MyData's preferred upload method (staging) requires approval from a MyTardis administrator.
This Contact Name will be used when sending confirmation that access to MyTardis's staging
area has been approved for this MyData instance.

**Contact Email**

MyData's preferred upload method (staging) requires approval from a MyTardis administrator.
This Contact Name will be used when sending confirmation that access to MyTardis's staging
area has been approved for this MyData instance.

**Data Directory**

Choose a folder where you would like to store your data.  (I chose "/Users/Shared/MyDataTest")

**MyTardis URL**

The URL of a MyTardis server running a MyTardis version compatible with MyData, e.g. http://118.138.241.91/

**MyTardis Username**

DO NOT put your individual MyTardis username (e.g. "wettenhj") in here.  Because MyData is 
designed to be able to upload multiple users' data from a instrument PC, the default username
used by MyData should generally be a shared facility role account.  For testing against 
http://118.138.241.91, we will use "testfacility".  Contact JW if you want the password for
this test account.

**MyTardis API Key**

<img src="https://github.com/monash-merc/mydata/blob/master/WalkthroughImages/DownloadApiKey.png" alt="Download API Key" style="width:200px;"/>

API keys are similar to passwords, but they are easier to revoke and renew when necessary.
Ask your MyTardis administrator for the API key corresponding to your facility role account.
Or if using the "testfacility" account with http://118.138.241.91, contact JW to obtain
the API key for that account.

Starting MyData's Scan and Upload Processes
-------------------------------------------
MyData will scan for data and attempt to upload it as soon as you click "OK" on the Settings dialog or whenever you press the refresh icon on MyData's toolbar.  If you launch MyData with a "--background" command-line argument, then it will automatically begin its scan and upload processes straight away, even without displaying its Settings dialog, assuming that valid settings have been entered previously.

MyData Upload Methods
---------------------
MyData supports two upload methods - HTTP POST and SCP via staging.

The HTTP POST upload method is only intended to be used for quick demos and for small data files.  Uploading large files with HTTP POST can put significant strain on the MyTardis server's resources (particularly memory usage).  The only advantage of HTTP POST is that it is easy to configure.  As long as you have access to a suitable MyTardis role account (e.g. "testfacility") and know its API key, then you can begin uploading from MyData straight away, although you should begin by testing small files only.

SCP via staging is MyData's preferred upload method.  MyData will automatically use this method as soon as it become available, but uploads via staging need to be approved by a MyTardis administrator.  MyData generates an SSH key pair the first time it runs and sends the public key to the MyTardis server in a request for the ability to upload via staging.  The MyTardis administrator needs to approve the request and put the public key in a suitable authorized keys file on the staging server (which could be the same as the MyTardis server).  For example, the public key could be put in "/home/mydata/.ssh/authorized_keys" on the staging server.

The first time a user runs MyData, they wil see a warning indicating that MyData's preferred upload method (SCP via staging) hasn't yet been approved by the MyTardis administartor:
<img src="https://github.com/monash-merc/mydata/blob/master/WalkthroughImages/UploadsToStagingRequireApprovalWarning.png" alt="Uploads To Staging Require Approval Warning", style="width:200px;"/>

The MyTardis administrator can approve the request in the Django Admin interface (after adding the public key to the appropriate /home/mydata/.ssh/authorized_keys file):
<img src="https://github.com/monash-merc/mydata/blob/master/WalkthroughImages/UploaderRegistrationApproval.png" alt="Uploader Registration Approval" style="width:200px;"/>

Once uploads to staging have been approved, MyData can manage multiple uploads at once (5 by default):
<img src="https://github.com/monash-merc/mydata/blob/master/WalkthroughImages/Multiple%20Upload%20Threads.png" alt="Multiple Upload Threads" style="width:200px;"/>

By clicking on the web browser icon on MyData's toolbar, you can view the uploaded data in MyTardis in your web browser.  The data will be jointly owned by the facility role account (e.g. "testfacility") and by the MyTardis user whose username (e.g. "wettenhj") was used to name the folder containing the datasets.  MyTardis allows grouping datasets together into experiments.  MyData uses the instrument name (e.g. "James Mac Laptop") and the date of creation of the dataset folders (e.g. "2014-12-18") to define a default experiment for the datasets it uploads:

<img src="https://github.com/monash-merc/mydata/blob/master/WalkthroughImages/DataInMyTardis.png" alt="Data In MyTardis" style="width:200px;"/>

If you are authorized to log into MyTardis's web interface as a facility manager, you can view the data in MyTardis's new Facility Overview.  Note the two owners - the facility role account ("testfacility") and the individual user ("wettenhj") who collected the data:


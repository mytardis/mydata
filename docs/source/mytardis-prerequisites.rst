MyTardis Prerequisites
======================

MyData has been developed against a fork of MyTardis's "develop" branch called
"mydata", which is currently a few commits behind MyTardis's "3.6" release,
but with some significant additions which are required for MyData.  Work is
underway to package the additions in the "mydata" MyTardis branch into a
separate MyTardis app to make them easy to install on top of an existing
MyTardis 3.6 installation.

The MyTardis branch which is currently used with MyData can be found here:
https://github.com/wettenhj/mytardis/tree/mydata

MyData stores metadata for each experiment it creates (usually including the
instrument name, the researcher's MyTardis username, and possibly the date of
collection of the data).  A schema must be added to MyTardis to support this:

  .. image:: images/ExperimentSchema.PNG

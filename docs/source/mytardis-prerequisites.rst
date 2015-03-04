MyTardis Prerequisites
======================

MyData is currently being developed against the "develop" branch of MyTardis,
and uses version "v1" of MyTardis's RESTful API.  A few additions to the API
are required by MyData.  The MyTardis branch which is currently used with
MyData can be found here: https://github.com/wettenhj/mytardis/tree/mydata

MyData stores metadata for each experiment it creates (usually including the
instrument name, the researcher's MyTardis username, and possibly the date of
collection of the data).  A schema must be added to MyTardis to support this:

  .. image:: images/ExperimentSchema.PNG

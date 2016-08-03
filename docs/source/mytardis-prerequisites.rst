MyTardis Prerequisites
======================

These instructions are for MyTardis server administrators who wish to support
uploads from MyData.

MyData requires the "mydata" MyTardis app to be installed on the MyTardis server.
This app, and its installation instructions can be found here:
https://github.com/mytardis/mytardis-app-mydata/blob/master/README.md

You should use the HEAD of the master branch of "mytardis-app-mydata", i.e.

::

    $ cd tardis/apps/
    $ git clone https://github.com/mytardis/mytardis-app-mydata mydata
    $ cd mydata

MyData stores metadata for each experiment it creates, including a reference
to the MyData instance (uploader) which created the experiment, and the name
of the user folder the experiment was created for.  A schema must be added to
MyTardis to support this:

  .. image:: images/ExperimentSchema.PNG

The final step of the instructions in
https://github.com/mytardis/mytardis-app-mydata/blob/master/README.md
describes how to create this schema, which is just a matter of running:

::

  python mytardis.py loaddata tardis/apps/mydata/fixtures/default_experiment_schema.json

after installing the "mytardis-app-mydata" MyTardis app in "tardis/apps/mydata".

MyData requires the use of a "receiving" storage box (also know as a "staging"
storage box) in MyTardis, which serves as a temporary location for uploaded
files.  MyTardis will automatically create a storage box if a client like
MyData attempts to perform staging uploads via the API.  To enable uploads via
staging (using SCP) in MyData, which are recommended over HTTP POST uploads,
it is necessary to add the "scp_username" and "scp_hostname" attributes to the
storage box, as illustrated below.

  .. image:: images/StorageBoxAttributes.png 

DEFAULT_RECEIVING_DIR in tardis/settings.py should be set to match the location
option of the "staging" (or "receiving") storage box, e.g.
"/var/lib/mytardis/receiving".  Similarly, DEFAULT_STORAGE_BASE_DIR in
tardis/settings.py should be set to match the location option of the "master"
storage box, which is called "default" above.

For more information on uploads via staging, see see :ref:`scp-to-staging`.

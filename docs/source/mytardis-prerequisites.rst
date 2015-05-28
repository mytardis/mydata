MyTardis Prerequisites
======================

For MyData v0.3.0, you should use the "MyData_v0.3.0" tag of MyTardis, i.e.

::

    $ git clone https://github.com/mytardis/mytardis develop
    $ cd develop
    $ git checkout -b MyData_v0.3.0 MyData_v0.3.0
    $ git describe --tags
    MyData_v0.3.0

MyData requires the "mydata" MyTardis app to be installed on the MyTardis server.
This app, and its installation instructions can be found here:
https://github.com/wettenhj/mytardis-app-mydata/blob/master/README.md

For MyData v0.3.0, you should use the "MyData_v0.3.0" tag of
"mytardis-app-mydata", i.e.

::

    $ cd tardis/apps/
    $ git clone https://github.com/wettenhj/mytardis-app-mydata mydata
    $ cd mydata
    $ git checkout -b MyData_v0.3.0 MyData_v0.3.0
    $ git describe --tags
    MyData_v0.3.0

MyData stores metadata for each experiment it creates, including a reference
to the MyData instance (uploader) which created the experiment, and the name
of the user folder the experiment was created for.  A schema must be added to
MyTardis to support this:

  .. image:: images/ExperimentSchema.PNG

The final step of the instructions in
https://github.com/wettenhj/mytardis-app-mydata/blob/master/README.md
describes how to create this schema, which is basically just a matter of
running:

::

  python mytardis.py loaddata tardis/apps/mydata/fixtures/default_experiment_schema.json

after installing the "mytardis-app-mydata" MyTardis app in "tardis/apps/mydata".

MyData requires the use of a "receiving" storage box (also know as a "staging" storage box)
in MyTardis, which serves as a temporary location for uploaded files.  MyTardis will
automatically create a storage box if a client like MyData attempts to perform staging
uploads via the API.  To enable uploads via staging (using SCP) in MyData, which are
recommended over HTTP POST uploads, it is necessary to add the "scp_username" and
"scp_hostname" attributes to the storage box, as illustrated below.

  .. image:: images/StorageBoxAttributes.png 

For more information on uploads via staging, see see :ref:`scp-to-staging`.

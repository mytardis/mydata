MyTardis Prerequisites
======================

MyData was originally developed against a fork of MyTardis's "develop" branch:
https://github.com/wettenhj/mytardis/tree/mydata.

Work is currently underway to move some of the functionality from the "mydata"
MyTardis branch into a separate "mydata" MyTardis app
(https://github.com/wettenhj/mytardis-app-mydata), merge some of it into
MyTardis's "develop" branch, and abandon its implementation of staging
uploads once it is confirmed that MyData can use MyTardis's new receiving
storage boxes: https://github.com/mytardis/mytardis/pull/414/commits

This will allow MyData's "develop" branch (which will soon become MyData v0.3)
to be used with MyTardis's "develop" branch (which may soon be tagged as v3.7).
Then the "mydata" branch of MyTardis in https://github.com/wettenhj/ will be
abandoned.

Instructions for installing the "mydata" MyTardis app can be found here:
https://github.com/wettenhj/mytardis-app-mydata/blob/master/README.md

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
